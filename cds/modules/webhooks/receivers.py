# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2020, 2020 CERN.
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

from __future__ import absolute_import, print_function

from copy import deepcopy

from celery.result import AsyncResult
from invenio_db import db
from invenio_files_rest.models import (
    ObjectVersion,
    ObjectVersionTag,
    as_object_version,
)
from invenio_records import Record
from sqlalchemy.orm.attributes import flag_modified
from flask import current_app, request, url_for

from cds_sorenson.api import get_all_distinct_qualities
from flask_security import current_user
from invenio_pidstore.models import PersistentIdentifier

from ._compat import delete_cached_json_for
from .errors import InvalidPayload
from ..deposit.api import deposit_video_resolver
from ..flows.api import Flow, Task
from ..flows.models import Status as FlowStatus
from ..records.permissions import DepositPermission

from .tasks import (
    DownloadTask,
    ExtractFramesTask,
    ExtractMetadataTask,
    TranscodeVideoTask,
    update_avc_deposit_state,
)


def _update_event_bucket(flow):
    """Update event's payload with correct bucket of deposit."""
    depid = flow.payload['deposit_id']
    dep_uuid = str(PersistentIdentifier.get('depid', depid).object_uuid)
    deposit_bucket = Record.get_record(dep_uuid)['_buckets']['deposit']
    flow.payload['bucket_id'] = deposit_bucket
    flag_modified(flow, 'payload')


class CeleryAsyncReceiver(object):
    """Celery Async Receiver abstract class."""

    def __call__(self):
        """Proxy to ``self.run`` method."""
        return self.run()

    def run(self, *args, **kwargs):
        """Implement method accepting the ``Event`` instance."""
        raise NotImplementedError()

    @staticmethod
    def get_flow(flow_id):
        """Find the latest flow associated with the event."""
        return Flow.get_flow(flow_id)

    def delete(self, flow):
        """Delete."""
        self.clean(flow=flow)

    def clean(self, flow):
        """Clean environment."""
        flow = CeleryAsyncReceiver.get_flow(flow.id)
        flow.stop()

    @staticmethod
    def delete_task(event, task_id):
        """Revoke a specific task."""
        AsyncResult(task_id).revoke(terminate=True)

    def serialize_result(self, flow):
        """Get the status."""
        flow = CeleryAsyncReceiver.get_flow(flow.id)
        if flow.response_code == 410:
            # in case the flow has been removed
            # return what was already in the response
            return 201, flow.response
        return FlowStatus.status_to_http(flow.status), flow.json

    def persist(self, flow):
        """Persist event and result after execution."""
        with db.session.begin_nested():

            status = CeleryAsyncReceiver.get_flow(flow.id).status
            flow.response.update(global_status=status)

        db.session.commit()
        update_avc_deposit_state(deposit_id=flow.payload.get('deposit_id'))

    def extract_payload(self):
        """Extract payload from request."""
        if request.is_json:
            # Request.get_json() could be first called with silent=True.
            delete_cached_json_for(request)
            return request.get_json(silent=False, cache=False)
        elif request.content_type == 'application/x-www-form-urlencoded':
            return dict(request.form)
        raise InvalidPayload(request.content_type)


class AVCWorkflow(CeleryAsyncReceiver):
    """AVC workflow receiver."""

    receiver_id = 'avc'

    def __init__(self, *args, **kwargs):
        """Init."""
        super(AVCWorkflow, self).__init__(*args, **kwargs)
        self._tasks = {
            'file_video_metadata_extraction': ExtractMetadataTask,
            'file_download': DownloadTask,
            'file_transcode': TranscodeVideoTask,
            'file_video_extract_frames': ExtractFramesTask,
        }

    def create_task(self, flow, task_name, **kwargs):
        """Create a task with parameters from flow."""
        payload = deepcopy(flow.payload)
        payload.update(**kwargs)
        return self._tasks[task_name](), payload

    def clean_task(self, flow, task_name, *args, **kwargs):
        """Clean a task."""
        kwargs['version_id'] = flow.payload['version_id']
        kwargs['deposit_id'] = flow.payload['deposit_id']
        return self._tasks[task_name]().clean(*args, **kwargs)

    @staticmethod
    def _init_object_version(flow):
        """Create, if doesn't exists, the version object."""
        flow_id = str(flow.id)
        with db.session.begin_nested():
            # create a object version if doesn't exists
            if 'version_id' in flow.payload:
                version_id = flow.payload['version_id']
                object_version = as_object_version(version_id)
            else:
                object_version = ObjectVersion.create(
                    bucket=flow.payload['bucket_id'], key=flow.payload['key']
                )
                ObjectVersionTag.create(
                    object_version, 'uri_origin', flow.payload['uri']
                )
                version_id = str(object_version.version_id)
            # add tag with corresponding event
            ObjectVersionTag.create_or_update(
                object_version, '_flow_id', flow_id
            )
            # add tag for preview
            ObjectVersionTag.create_or_update(object_version, 'preview', True)
            # add tags for file type
            ObjectVersionTag.create_or_update(
                object_version, 'media_type', 'video'
            )
            ObjectVersionTag.create_or_update(
                object_version, 'context_type', 'master'
            )
            flow.response['version_id'] = version_id
        return object_version

    @staticmethod
    def _update_flow_response(flow, version_id):
        """Update event response."""
        flow_id = str(flow.id)
        object_version = as_object_version(version_id)
        obj_tags = object_version.get_tags()
        obj_key = object_version.key
        obj_bucket_id = str(object_version.bucket_id)
        with db.session.begin_nested():
            flow.response.update(
                links={
                    'self': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=obj_bucket_id,
                        key=obj_key,
                        _external=True,
                    ),
                    'cancel': url_for(
                        'cds_webhooks.flow_item',
                        receiver_id=AVCWorkflow.receiver_id,
                        flow_id=flow_id,
                        _external=True,
                    ),
                },
                key=obj_key,
                version_id=version_id,
                tags=obj_tags,
            )
            flag_modified(flow.model, 'response')

    def _build_flow(self, flow):
        """Build flow."""

        # First step
        if 'version_id' in flow.payload:
            flow.chain(
                *self.create_task(
                    flow=flow, task_name='file_video_metadata_extraction'
                )
            )
        else:
            # FIXME: better handle this on the API
            tasks_info = [
                list(t)
                for t in zip(
                    self.create_task(
                        flow=flow, task_name='file_download'
                    ),
                    self.create_task(
                        flow=flow,
                        task_name='file_video_metadata_extraction',
                    ),
                )
            ]
            flow.group(*tasks_info)
        # Second step
        all_distinct_qualities = get_all_distinct_qualities()
        flow.response['presets'] = all_distinct_qualities

        tasks_info = [
            list(t)
            for t in zip(
                self.create_task(
                    flow=flow, task_name='file_video_extract_frames'
                ),
                *[
                    self.create_task(
                        flow=flow,
                        task_name='file_transcode',
                        preset_quality=preset_quality,
                    )
                    for preset_quality in all_distinct_qualities
                ]
            )
        ]
        flow.group(*tasks_info)

        return flow

    def _workflow(self, deposit_id, user_id, bucket_id, version_id, key):
        with db.session.begin_nested():
            # Add the event ID to the payload for querying later
            flow = Flow.create(
                'AVCWorkflow',
                payload={
                    'deposit_id': deposit_id,
                    'bucket_id': bucket_id,
                    'version_id': version_id,
                    'key': key,

                },
                user_id=user_id,
                deposit_id=deposit_id,
                receiver_id=self.receiver_id,
            )
            flow.assemble(self._build_flow)
        db.session.commit()
        return flow

    def run(self, deposit_id, user_id, version_id, bucket_id, key):
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

        flow = self._workflow(deposit_id=deposit_id,
                              user_id=user_id,
                              bucket_id=bucket_id,
                              version_id=version_id,
                              key=key)
        flow_id = flow.id  # Get it for later because the DB object is modified
        assert 'deposit_id' in flow.payload
        assert ('uri' in flow.payload and 'key' in flow.payload) or (
                'version_id' in flow.payload
        )

        if 'version_id' not in flow.payload:
            _update_event_bucket(flow)

        # 1. create the object version if doesn't exist
        object_version = self._init_object_version(flow)
        version_id = str(object_version.version_id)

        # expunge in case of any mutations to the object
        db.session.expunge(flow.model)
        db.session.commit()

        # 2. define the workflow and run
        flow.start()
        # 2.1 Refresh flow object
        flow = Flow.get_flow(flow_id)
        # 3. update event response
        self._update_flow_response(flow=flow, version_id=version_id)

        # 4. persist everything
        super(AVCWorkflow, self).persist(flow)

        return flow

    def clean(self, flow):
        """Delete tasks and everything created by them."""
        self.clean_task(flow=flow, task_name='file_video_extract_frames')
        for preset_quality in get_all_distinct_qualities():
            self.clean_task(
                flow=flow,
                task_name='file_transcode',
                preset_quality=preset_quality,
            )
        self.clean_task(
            flow=flow, task_name='file_video_metadata_extraction'
        )
        if 'version_id' not in flow.payload:
            self.clean_task(flow=flow, task_name='file_download')
        super(AVCWorkflow, self).clean(flow)

    def serialize_result(self, flow):
        """AVCWorkflow particular status."""
        code, full_flow_json = super(AVCWorkflow, self).serialize_result(flow)
        if 'tasks' in full_flow_json:
            # Extract info and build correct status dict
            full_flow_json = self.build_flow_json(full_flow_json)
        return code, full_flow_json

    def build_flow_json(self, flow_json):
        """Build json serializer object."""
        status = ([], [])

        for task in flow_json['tasks']:
            task_status = Task.build_task_json_status(task)

            # Get the UI name of the task
            task_name = task_status["name"]

            # Calculate the right position inside the tuple
            step = (
                0
                if task_name
                in ('file_download', 'file_video_metadata_extraction')
                else 1
            )

            status[step].append(task_status)

        return status

    @classmethod
    def can(cls, user_id, flow, action, **kwargs):
        """Check receiver permission."""
        record = None
        if flow:
            deposit_id = flow.payload['deposit_id']
            record = deposit_video_resolver(deposit_id).project
        return DepositPermission.create(
            record=record, action=action, user=current_user
        ).can()
