# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Webhook Receivers."""

from __future__ import absolute_import

from copy import deepcopy

from flask_security import current_user
from cds_sorenson.api import get_all_distinct_qualities
from celery import chain, group
from celery.result import AsyncResult
from invenio_db import db
from celery import states
from flask import url_for
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified
from celery.result import result_from_tuple

from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)

from .status import ComputeGlobalStatus, iterate_result, collect_info, \
    GetInfoByID, replace_task_id, ResultEncoder
from .tasks import DownloadTask, ExtractFramesTask, ExtractMetadataTask, \
    TranscodeVideoTask, update_avc_deposit_state
from ..records.permissions import DepositPermission
from ..deposit.api import deposit_video_resolver


def _update_event_bucket(event):
    """Update event's payload with correct bucket of deposit."""
    depid = event.payload['deposit_id']
    dep_uuid = str(PersistentIdentifier.get('depid', depid).object_uuid)
    deposit_bucket = Record.get_record(dep_uuid)['_buckets']['deposit']
    event.payload['bucket_id'] = deposit_bucket
    flag_modified(event, 'payload')


def build_task_payload(event, task_id):
    """Build payload for a task."""
    raw_info = event.receiver._raw_info(event=event)
    search = GetInfoByID(task_id=task_id)
    iterate_result(raw_info=raw_info, fun=search)
    if search.task_name:
        if isinstance(search.result.info, Exception):
            if hasattr(search.result.info, 'message'):
                payload = search.result.info.message['payload']
            else:
                payload = search.result.info.args[0]['payload']
        else:
            payload = search.result.info['payload']
        base = {
            'event': event, 'task_name': search.task_name, 'task_id': task_id
        }
        base.update(**payload)
        return base


class CeleryAsyncReceiver(Receiver):
    """Celery Async Receiver abstract class."""

    CELERY_STATES_TO_HTTP = {
        states.PENDING: 202,
        states.STARTED: 202,
        states.RETRY: 202,
        states.FAILURE: 500,
        states.SUCCESS: 201,
        states.REVOKED: 409,
    }
    """Mapping of Celery result states to HTTP codes."""

    @staticmethod
    def has_result(event):
        """Return true if some result are in the event."""
        return '_tasks' in event.response

    @classmethod
    def _deserialize_result(cls, event):
        """Deserialize celery result stored in event."""
        result = result_from_tuple(event.response['_tasks']['result'])
        parent = result_from_tuple(event.response['_tasks']['parent']) \
            if 'parent' in event.response['_tasks'] else None
        result.parent = parent
        return result

    @classmethod
    def _serialize_result(cls, event, result, fun=None):
        """Run the task and save the task ids."""
        fun = fun or (lambda x: x)
        with db.session.begin_nested():
            event.response.update(
                _tasks={
                    'result': fun(result.as_tuple()),
                }
            )
            if result.parent:
                event.response['_tasks']['parent'] = fun(
                    result.parent.as_tuple())
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def delete(self, event):
        """Delete."""
        self.clean(event=event)
        super(CeleryAsyncReceiver, self).delete(event=event)

    def clean(self, event):
        """Clean environment."""
        iterate_result(
            raw_info=self._raw_info(event),
            fun=lambda task_name, result: result.revoke(terminate=True))
        super(CeleryAsyncReceiver, self).clean(event=event)

    @staticmethod
    def delete_task(event, task_id):
        """Revoke a specific task."""
        AsyncResult(task_id).revoke(terminate=True)

    def status(self, event):
        """Get the status."""
        if event.response_code == 410:
            # in case the event has been removed
            return (201, event.response)
        # get raw info from the celery receiver
        raw_info = self._raw_info(event)
        # extract global status
        global_status = ComputeGlobalStatus()
        iterate_result(raw_info=raw_info, fun=global_status)
        # extract information
        info = iterate_result(raw_info=raw_info, fun=collect_info)
        # build response
        return (
            CeleryAsyncReceiver.CELERY_STATES_TO_HTTP.get(
                global_status.status),
            ResultEncoder().encode(info)
        )

    def persist(self, event, result):
        """Persist event and result after execution."""
        with db.session.begin_nested():
            status = iterate_result(
                raw_info=self._raw_info(event),
                fun=lambda task_name, result: {
                    task_name: {
                        'id': result.id,
                        'status': result.status
                    }
                })
            event.response.update(global_status=status)

            db.session.add(event)
        db.session.commit()
        update_avc_deposit_state(deposit_id=event.payload.get('deposit_id'))

    def rerun_task(self, **payload):
        """Re-run a task."""
        db.session.expunge(payload['event'])
        # rerun task (with cleaning)
        result = self.run_task(_clean=True, **payload).apply_async()
        # update event information
        self._update_serialized_result(
            event=payload['event'], old_task_id=payload['task_id'],
            task_result=result)
        self.persist(event=payload['event'],
                     result=self._deserialize_result(payload['event']))

    def _update_serialized_result(self, event, old_task_id, task_result):
        """Update task id in global result."""
        result_deserialized = self._deserialize_result(event)
        self._serialize_result(
            event=event, result=result_deserialized,
            fun=lambda x: replace_task_id(
                result=x, old_task_id=old_task_id, new_task_id=task_result.id))


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    @staticmethod
    def _init_object_version(event):
        """Create the version object."""
        event_id = str(event.id)
        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])
            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event_id)
            ObjectVersionTag.create(object_version, 'context_type', 'master')
        return object_version

    @staticmethod
    def _workflow(event, version_id):
        """Define the workflow."""
        event_id = str(event.id)
        return DownloadTask().s(
            version_id=version_id,
            event_id=event_id,
            **event.payload)

    @staticmethod
    def _update_event_response(event, version_id):
        """Update event response."""
        event_id = str(event.id)
        object_version = as_object_version(version_id)
        obj_tags = object_version.get_tags()
        bucket_id = str(object_version.bucket_id)
        object_version_key = object_version.key
        with db.session.begin_nested():
            event.response.update(
                links={
                    'self': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=bucket_id,
                        key=object_version_key,
                        _external=True, ),
                    'version': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=bucket_id,
                        key=object_version_key,
                        versionId=version_id,
                        _external=True, ),
                    'cancel': url_for(
                        'invenio_webhooks.event_item',
                        receiver_id='downloader',
                        event_id=event_id,
                        _external=True,
                    ),
                },
                key=object_version_key,
                version_id=version_id,
                tags=obj_tags,
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def run(self, event):
        """Create object version and send celery task to download.

        Mandatory fields in the payload:
          * uri, location to download the view.
          * bucket_id
          * key, file name.
          * deposit_id

        For more info see the task
        :func: `~cds.modules.webhooks.tasks.DownloadTask` this
        receiver is using.
        """
        assert 'uri' in event.payload
        assert 'key' in event.payload
        assert 'deposit_id' in event.payload

        # TODO remove field completely when we make sure nothing breaks
        _update_event_bucket(event)

        # 1. create the object version
        object_version = self._init_object_version(event=event)
        version_id = str(object_version.version_id)
        db.session.expunge(event)
        db.session.expunge(object_version)
        db.session.commit()
        # 2. define the workflow and run
        result = self._workflow(
            event=event, version_id=version_id).apply_async()
        # 3. update event response
        self._update_event_response(event=event, version_id=version_id)
        # 4. serialize event and result
        self._serialize_result(event=event, result=result)
        # 5. persist everything
        super(Downloader, self).persist(event=event, result=result)

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        return {'file_download': result}

    def clean(self, event):
        """Delete generated files."""
        self.clean_task(event=event, task_name='file_download')
        super(Downloader, self).clean(event)

    @staticmethod
    def clean_task(event, task_name, *args, **kwargs):
        """Delete everything created by a task."""
        if task_name == 'file_download':
            DownloadTask().clean(version_id=event.response['version_id'])


class AVCWorkflow(CeleryAsyncReceiver):
    """AVC workflow receiver."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super(AVCWorkflow, self).__init__(*args, **kwargs)
        self._tasks = {
            'file_video_metadata_extraction': ExtractMetadataTask,
            'file_download': DownloadTask,
            'file_transcode': TranscodeVideoTask,
            'file_video_extract_frames': ExtractFramesTask,
        }

    def run_task(self, event, task_name, *args, **kwargs):
        """Run a task."""
        kwargs['event_id'] = str(event.id)
        kwargs['version_id'] = event.response['version_id']
        payload = deepcopy(event.payload)
        payload.update(**kwargs)
        return self._tasks[task_name]().si(*args, **payload)

    def clean_task(self, event, task_name, *args, **kwargs):
        """Clean a task."""
        kwargs['event_id'] = str(event.id)
        kwargs['version_id'] = event.response['version_id']
        kwargs['deposit_id'] = event.payload['deposit_id']
        return self._tasks[task_name]().clean(*args, **kwargs)

    @staticmethod
    def _init_object_version(event):
        """Create, if doesn't exists, the version object."""
        event_id = str(event.id)
        with db.session.begin_nested():
            # create a object version if doesn't exists
            if 'version_id' in event.payload:
                version_id = event.payload['version_id']
                object_version = as_object_version(version_id)
            else:
                object_version = ObjectVersion.create(
                    bucket=event.payload['bucket_id'],
                    key=event.payload['key'])
                ObjectVersionTag.create(object_version, 'uri_origin',
                                        event.payload['uri'])
                version_id = str(object_version.version_id)
            # add tag with corresponding event
            ObjectVersionTag.create_or_update(
                object_version, '_event_id', event_id)
            # add tag for preview
            ObjectVersionTag.create_or_update(object_version, 'preview', True)
            # add tags for file type
            ObjectVersionTag.create_or_update(
                object_version, 'media_type', 'video')
            ObjectVersionTag.create_or_update(
                object_version, 'context_type', 'master')
            event.response['version_id'] = version_id
        return object_version

    @staticmethod
    def _update_event_response(event, version_id):
        """Update event response."""
        event_id = str(event.id)
        object_version = as_object_version(version_id)
        obj_tags = object_version.get_tags()
        obj_key = object_version.key
        obj_bucket_id = str(object_version.bucket_id)
        with db.session.begin_nested():
            event.response.update(
                links={
                    'self': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=obj_bucket_id,
                        key=obj_key,
                        _external=True,
                    ),
                    'cancel': url_for(
                        'invenio_webhooks.event_item',
                        receiver_id='avc',
                        event_id=event_id,
                        _external=True,
                    ),
                },
                key=obj_key,
                version_id=version_id,
                tags=obj_tags,
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def _first_step(self, event):
        """Define first step."""
        with db.session.begin_nested():
            if 'version_id' in event.payload:
                first_step = self.run_task(
                    event=event, task_name='file_video_metadata_extraction')
            else:
                first_step = group(
                    self.run_task(event=event, task_name='file_download'),
                    self.run_task(event=event,
                                  task_name='file_video_metadata_extraction'),
                )
        return first_step

    def _second_step(self, event):
        """Define second step."""
        all_distinct_qualities = get_all_distinct_qualities()
        event.response['presets'] = all_distinct_qualities
        return group(
            self.run_task(event=event, task_name='file_video_extract_frames'),
            *[self.run_task(
                event=event, task_name='file_transcode',
                preset_quality=preset_quality)
              for preset_quality in all_distinct_qualities]
        )

    def _workflow(self, event):
        first_step = self._first_step(event=event)
        second_step = self._second_step(event=event)
        return chain(first_step, second_step)

    def run(self, event):
        """Run AVC workflow for video transcoding.

        Steps:
          * Download the video file (if not done yet).
          * Extract metadata from the video.
          * Run video transcoding.
          * Extract frames from the video.

        Mandatory fields in the payload:
          * uri, if the video needs to be downloaded.
          * bucket_id, only if URI is provided.
          * key, only if URI is provided.
          * version_id, if the video has been downloaded via HTTP (the previous
            fields are not needed in this case).
          * deposit_id

        Optional:
          * frames_start, if not set the default value will be used.
          * frames_end, if not set the default value will be used.
          * frames_gap, if not set the default value will be used.

        For more info see the tasks used in the workflow:
          * :func: `~cds.modules.webhooks.tasks.DownloadTask`
          * :func: `~cds.modules.webhooks.tasks.ExtractMetadataTask`
          * :func: `~cds.modules.webhooks.tasks.ExtractFramesTask`
          * :func: `~cds.modules.webhooks.tasks.TranscodeVideoTask`
        """
        assert 'deposit_id' in event.payload
        assert (('uri' in event.payload and 'key' in event.payload)
                or ('version_id' in event.payload))

        # TODO remove field completely when we make sure nothing breaks
        if 'version_id' not in event.payload:
            _update_event_bucket(event)

        # 1. create the object version if doesn't exist
        object_version = self._init_object_version(event=event)
        version_id = str(object_version.version_id)
        db.session.expunge(event)
        db.session.commit()
        # 2. define the workflow and run
        result = self._workflow(event=event).apply_async()
        # 3. update event response
        self._update_event_response(event=event, version_id=version_id)
        # 4. serialize event and result
        self._serialize_result(event=event, result=result)
        # 5. persist everything
        super(AVCWorkflow, self).persist(event, result)

    def clean(self, event):
        """Delete tasks and everything created by them."""
        self.clean_task(event=event, task_name='file_video_extract_frames')
        for preset_quality in get_all_distinct_qualities():
            self.clean_task(
                event=event, task_name='file_transcode',
                preset_quality=preset_quality)
        self.clean_task(
            event=event, task_name='file_video_metadata_extraction')
        if 'version_id' not in event.payload:
            self.clean_task(event=event, task_name='file_download')
        super(AVCWorkflow, self).clean(event)

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        if 'version_id' in event.payload:
            first_step = [{'file_video_metadata_extraction': result.parent}]
        else:
            first_step = [
                {'file_download': result.parent.children[0]},
                {'file_video_metadata_extraction': result.parent.children[1]}
            ]
        second_step = [{'file_video_extract_frames': result.children[0]}]
        for res in result.children[1:]:
            second_step.append({'file_transcode': res})
        return first_step, second_step

    @classmethod
    def can(cls, user_id, event, action, **kwargs):
        """Check permission."""
        record = None
        if event:
            deposit_id = event.payload['deposit_id']
            record = deposit_video_resolver(deposit_id).project
        return DepositPermission.create(
            record=record, action=action, user=current_user).can()
