# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

import json

from copy import deepcopy

from cds_sorenson.api import get_available_preset_qualities
from celery import chain, group
from celery.result import AsyncResult
from invenio_db import db
from celery import states
from flask import url_for
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified
from celery.result import result_from_tuple

from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)

from .status import ComputeGlobalStatus, iterate_result, collect_info
from .tasks import DownloadTask, ExtractFramesTask, ExtractMetadataTask, \
    TranscodeVideoTask, update_deposit_state


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

    def has_result(self, event):
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
    def _serialize_result(cls, event, result):
        """Run the task and save the task ids."""
        with db.session.begin_nested():
            event.response.update(
                _tasks={
                    'result': result.as_tuple(),
                }
            )
            if result.parent:
                event.response['_tasks']['parent'] = result.parent.as_tuple()
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def delete(self, event):
        """Revoke all associated tasks."""
        iterate_result(
            raw_info=self._raw_info(event),
            fun=lambda task_name, result: result.revoke(terminate=True))

    def delete_task(self, event, task_id):
        """Revoke a specific task."""
        AsyncResult(task_id).revoke(terminate=True)

    def status(self, event):
        """Get the status."""
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
            json.dumps(info)
        )

    def persist(self, event, result):
        """Persist event and result after execution."""
        with db.session.begin_nested():
            self._serialize_result(event=event, result=result)

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
        update_deposit_state(
            deposit_id=event.payload.get('deposit_id'),
            event_id=event.id,
            sse_channel=event.payload.get('sse_channel')
        )


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    def _init_object_version(self, event):
        """Create the version object."""
        event_id = str(event.id)
        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])
            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event_id)
        return object_version

    def _workflow(self, event, version_id):
        """Define the workflow."""
        event_id = str(event.id)
        return DownloadTask().s(
            version_id=version_id,
            event_id=event_id,
            **event.payload)

    def _update_event_response(self, event, version_id):
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

        Optional:
          * sse_channel, if set all the tasks will publish their status update
            to it.

        For more info see the task
        :func: `~cds.modules.webhooks.tasks.DownloadTask` this
        receiver is using.
        """
        assert 'bucket_id' in event.payload
        assert 'uri' in event.payload
        assert 'key' in event.payload
        assert 'deposit_id' in event.payload

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
        super(Downloader, self).persist(event=event, result=result)

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        return {"file_download": result}

    def delete(self, event):
        """Delete generated files."""
        super(Downloader, self).delete(event)
        self.clean_task(event=event, task_name='file_download')

    def clean_task(self, event, task_name, *args, **kwargs):
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

    def _init_object_version(self, event):
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
            # and a tag associated to him
            ObjectVersionTag.create(object_version, '_event_id', event_id)
            # save in response the version_id
            event.response['version_id'] = version_id
        return object_version

    def _update_event_response(self, event, version_id):
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
        preset_qualities = get_available_preset_qualities()
        event.response['presets'] = preset_qualities
        return group(
            self.run_task(event=event, task_name='file_video_extract_frames'),
            *[self.run_task(
                event=event, task_name='file_transcode',
                preset_quality=preset_quality)
              for preset_quality in preset_qualities]
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
          * sse_channel, if set all the tasks will publish their status update
            to it.
          * frames_start, if not set the default value will be used.
          * frames_end, if not set the default value will be used.
          * frames_gap, if not set the default value will be used.

        For more info see the tasks used in the workflow:
          * :func: `~cds.modules.webhooks.tasks.DownloadTask`
          * :func: `~cds.modules.webhooks.tasks.ExtractMetadataTask`
          * :func: `~cds.modules.webhooks.tasks.ExtractFramesTask`
          * :func: `~cds.modules.webhooks.tasks.TranscodeVideoTask`
        """
        assert ('uri' in event.payload and 'bucket_id' in event.payload and
                'key' in event.payload) or ('version_id' in event.payload)
        assert 'deposit_id' in event.payload

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
        super(AVCWorkflow, self).persist(event, result)

    def delete(self, event):
        """Delete tasks and everything created by them."""
        super(AVCWorkflow, self).delete(event)
        self.clean_task(event=event, task_name='file_video_extract_frames')
        for preset_quality in get_available_preset_qualities():
            self.clean_task(
                event=event, task_name='file_transcode',
                preset_quality=preset_quality)
        self.clean_task(
            event=event, task_name='file_video_metadata_extraction')
        if 'version_id' not in event.payload:
            self.clean_task(event=event, task_name='file_download')
        self.clean(event=event)

    def clean(self, event):
        """Delete the event."""
        with db.session.begin_nested():
            ObjectVersionTag.query.filter_by(
                key='_event_id', value=str(event.id)).delete()

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        if 'version_id' in event.payload:
            first_step = [{"file_video_metadata_extraction": result.parent}]
        else:
            first_step = [
                {"file_download": result.parent.children[0]},
                {"file_video_metadata_extraction": result.parent.children[1]}
            ]
        second_step = [{"file_video_extract_frames": result.children[0]}]
        for res in result.children[1:]:
            second_step.append({"file_transcode": res})
        return first_step, second_step
