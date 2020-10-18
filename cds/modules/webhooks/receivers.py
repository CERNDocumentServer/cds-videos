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

import json
from copy import deepcopy

from celery.result import AsyncResult
from flask import url_for
from invenio_db import db
from invenio_files_rest.models import (
    ObjectVersion,
    ObjectVersionTag,
    as_object_version,
)
from invenio_records import Record
from sqlalchemy.orm.attributes import flag_modified

from cds_sorenson.api import get_all_distinct_qualities
from flask_security import current_user
from invenio_pidstore.models import PersistentIdentifier
from invenio_webhooks.models import Receiver

from ..deposit.api import deposit_video_resolver
from ..flows.api import Flow
from ..flows.models import Status as FlowStatus
from ..records.permissions import DepositPermission
from .status import (
    get_event_last_flow,
    replace_task_id,
    TASK_NAMES,
)
from .tasks import (
    DownloadTask,
    ExtractFramesTask,
    ExtractMetadataTask,
    TranscodeVideoTask,
    update_avc_deposit_state,
)


def _update_event_bucket(event):
    """Update event's payload with correct bucket of deposit."""
    depid = event.payload['deposit_id']
    dep_uuid = str(PersistentIdentifier.get('depid', depid).object_uuid)
    deposit_bucket = Record.get_record(dep_uuid)['_buckets']['deposit']
    event.payload['bucket_id'] = deposit_bucket
    flag_modified(event, 'payload')


class CeleryAsyncReceiver(Receiver):
    """Celery Async Receiver abstract class."""

    @staticmethod
    def has_result(event):
        """Return true if some result are in the event."""
        return '_tasks' in event.response

    @staticmethod
    def get_flow(event):
        """Find the latest flow associated with the event."""
        return get_event_last_flow(event)

    @classmethod
    def _deserialize_result(cls, event):
        """Deserialize celery result stored in event."""
        return CeleryAsyncReceiver.get_flow(event).status

    @classmethod
    def _serialize_result(cls, event, result, fun=None):
        """Run the task and save the task ids."""
        fun = fun or (lambda x: x)
        with db.session.begin_nested():
            event.response.update(_tasks=result)
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def delete(self, event):
        """Delete."""
        self.clean(event=event)
        super(CeleryAsyncReceiver, self).delete(event=event)

    def clean(self, event):
        """Clean environment."""
        flow = CeleryAsyncReceiver.get_flow(event)
        flow.stop()
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
        status = CeleryAsyncReceiver.get_flow(event).status
        return (FlowStatus.status_to_http(status['status']), status)

    def persist(self, event, result):
        """Persist event and result after execution."""
        with db.session.begin_nested():
            status = CeleryAsyncReceiver.get_flow(event).status
            event.response.update(global_status=status['status'])

            db.session.add(event)
        db.session.commit()
        update_avc_deposit_state(deposit_id=event.payload.get('deposit_id'))

    def rerun_task(self, **payload):
        """Re-run a task."""
        # TODO
        db.session.expunge(payload['event'])
        # rerun task (with cleaning)
        result = self.run_task(_clean=True, **payload).apply_async()
        # update event information
        self._update_serialized_result(
            event=payload['event'],
            old_task_id=payload['task_id'],
            task_result=result,
        )
        self.persist(
            event=payload['event'],
            result=self._deserialize_result(payload['event']),
        )

    def _update_serialized_result(self, event, old_task_id, task_result):
        """Update task id in global result."""
        # TODO
        result_deserialized = self._deserialize_result(event)
        self._serialize_result(
            event=event,
            result=result_deserialized,
            fun=lambda x: replace_task_id(
                result=x, old_task_id=old_task_id, new_task_id=task_result.id
            ),
        )


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

    def create_task(self, event, task_name, **kwargs):
        """Create a task with parameters from event."""
        kwargs['event_id'] = str(event.id)
        kwargs['version_id'] = event.response['version_id']
        payload = deepcopy(event.payload)
        payload.update(**kwargs)
        return (self._tasks[task_name](), payload)

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
                    bucket=event.payload['bucket_id'], key=event.payload['key']
                )
                ObjectVersionTag.create(
                    object_version, 'uri_origin', event.payload['uri']
                )
                version_id = str(object_version.version_id)
            # add tag with corresponding event
            ObjectVersionTag.create_or_update(
                object_version, '_event_id', event_id
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

    def _build_flow(self, event):
        """Build flow."""

        def build_flow(flow):
            # First step
            if 'version_id' in event.payload:
                flow.chain(
                    *self.create_task(
                        event=event, task_name='file_video_metadata_extraction'
                    )
                )
            else:
                # FIXME: better handle this on the API
                tasks_info = [
                    list(t)
                    for t in zip(
                        self.create_task(
                            event=event, task_name='file_download'
                        ),
                        self.create_task(
                            event=event,
                            task_name='file_video_metadata_extraction',
                        ),
                    )
                ]
                flow.group(*tasks_info)
            # Second step
            all_distinct_qualities = get_all_distinct_qualities()
            event.response['presets'] = all_distinct_qualities

            tasks_info = [
                list(t)
                for t in zip(
                    self.create_task(
                        event=event, task_name='file_video_extract_frames'
                    ),
                    *[
                        self.create_task(
                            event=event,
                            task_name='file_transcode',
                            preset_quality=preset_quality,
                        )
                        for preset_quality in all_distinct_qualities
                    ]
                )
            ]
            flow.group(*tasks_info)

        return build_flow

    def _workflow(self, event):
        with db.session.begin_nested():
            # Add the event ID to the payload for querying later
            flow = Flow.create(
                'AVCWorkflow',
                payload={
                    'event_id': str(event.id),
                    'deposit_id': event.payload['deposit_id'],
                },
            )
            flow.assemble(self._build_flow(event))
        db.session.commit()
        return flow

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
        assert ('uri' in event.payload and 'key' in event.payload) or (
            'version_id' in event.payload
        )

        # TODO remove field completely when we make sure nothing breaks
        if 'version_id' not in event.payload:
            _update_event_bucket(event)

        # 1. create the object version if doesn't exist
        object_version = self._init_object_version(event=event)
        version_id = str(object_version.version_id)
        db.session.expunge(event)
        db.session.commit()
        # 2. define the workflow and run
        flow = self._workflow(event=event)
        flow_id = flow.id # Get it for later because the DB object is modified
        flow.start()
        # 2.1 Refresh flow object
        flow = Flow.get_flow(flow_id)
        # 3. update event response
        self._update_event_response(event=event, version_id=version_id)
        # 4. serialize event and result
        self._serialize_result(
            event=event, result=self.build_status(flow.status)
        )
        # 5. persist everything
        super(AVCWorkflow, self).persist(event, flow.status)

    def clean(self, event):
        """Delete tasks and everything created by them."""
        self.clean_task(event=event, task_name='file_video_extract_frames')
        for preset_quality in get_all_distinct_qualities():
            self.clean_task(
                event=event,
                task_name='file_transcode',
                preset_quality=preset_quality,
            )
        self.clean_task(
            event=event, task_name='file_video_metadata_extraction'
        )
        if 'version_id' not in event.payload:
            self.clean_task(event=event, task_name='file_download')
        super(AVCWorkflow, self).clean(event)

    def status(self, event):
        """AVCWorkflow particular status."""
        code, status = super(AVCWorkflow, self).status(event)
        if 'tasks' in status:
            # Extract info and build correct status dict
            status = self.build_status(status)
        return code, status

    def build_status(self, raw_info):
        status = ([], [])
        for task in raw_info['tasks']:
            # Get the UI name of the task
            task_name = TASK_NAMES.get(task['name'])
            # Calculate the right position inside the tuple
            step = (
                0
                if task_name
                in ('file_download', 'file_video_metadata_extraction')
                else 1
            )
            # Add the information the UI needs on the right position
            payload = task['payload']
            payload['type'] = task_name
            payload['key'] = payload.get('preset_quality', payload['key'])
            if task_name == 'file_video_metadata_extraction':
                # Load message as JSON, we only need this for this particular task
                try:
                    payload['extracted_metadata'] = json.loads(task['message'])
                except:
                    payload['extracted_metadata'] = task['message']
                task['message'] = 'Attached video metadata'
            status[step].append(
                {
                    'name': task_name,
                    'id': task['id'],
                    'status': 'REVOKED'
                    if 'Not transcoding' in task['message']
                    else task['status'],
                    'info': {
                        'payload': payload,
                        'message': task['message'],
                    },
                }
            )

        return status

    @classmethod
    def can(cls, user_id, event, action, **kwargs):
        """Check permission."""
        record = None
        if event:
            deposit_id = event.payload['deposit_id']
            record = deposit_video_resolver(deposit_id).project
        return DepositPermission.create(
            record=record, action=action, user=current_user
        ).can()
