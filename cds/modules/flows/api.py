# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2020 CERN.
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

"""CDS-Flow python API."""
import logging
from copy import deepcopy

from cds_sorenson.api import get_all_distinct_qualities
from celery import chain as celery_chain
from celery import group as celery_group
from celery.result import AsyncResult
from invenio_db import db
from sqlalchemy.orm.attributes import flag_modified

from .deposit import update_deposit_state
from .files import init_object_version
from .models import Flow as FlowModel
from .models import Task as TaskModel
from .task_api import Task
from .utils import uuid
from .tasks import ExtractMetadataTask, DownloadTask, \
    TranscodeVideoTask, ExtractFramesTask

logger = logging.getLogger('cds-flow')


class FlowWrapper(object):
    """Flow Model wrapper class."""

    def __init__(self, model=None):
        """Initialize the flow object."""
        self.model = model

    @property
    def id(self):
        """Get flow identifier."""
        return self.model.id if self.model else None

    @property
    def deposit_id(self):
        """Get flow identifier."""
        return self.model.deposit_id if self.model else None

    @property
    def name(self):
        """Get flow name."""
        return self.model.name if self.model else None

    @property
    def payload(self):
        """Get flow payload."""
        return self.model.payload if self.model else None

    @payload.setter
    def payload(self, value):
        """Update payload."""
        if self.model:
            self.model.payload = value
            db.session.merge(self.model)

    @property
    def created(self):
        """Get creation timestamp."""
        return self.model.created if self.model else None

    @property
    def updated(self):
        """Get last updated timestamp."""
        return self.model.updated if self.model else None

    @property
    def json(self):
        """Get flow status."""
        if self.model is None:
            return None
        res = self.model.to_dict()
        res.update(
            {'tasks': [t.to_dict() for t in self.model.tasks]}
        )
        return res

    @property
    def status(self):
        return self.model.status if self.model else None

    @classmethod
    def get_flow(cls, id_):
        """Retrieve a Flow from the database by Id."""
        obj = FlowModel.get(id_)
        return cls(model=obj)

    @property
    def deleted(self):
        """Get flow payload."""
        return self.model.deleted if self.model else None

    @deleted.setter
    def deleted(self, value):
        """Update payload."""
        if self.model:
            self.model.deleted = value
            db.session.merge(self.model)

    @classmethod
    def get(cls, flow_id):
        obj = FlowModel.query.filter(FlowModel.id == flow_id).one()
        return cls(model=obj)

    @classmethod
    def get_for_deposit(cls, deposit_id):
        obj = FlowModel.query.filter(FlowModel.deposit_id == deposit_id) \
            .one()
        return cls(model=obj)

    @classmethod
    def create(cls, name, deposit_id, payload=None, user_id=None):
        """Create a new flow instance and store it in the database."""
        with db.session.begin_nested():
            obj = FlowModel(
                name=name,
                id=uuid(),
                payload=payload or dict(),
                user_id=user_id,
                deposit_id=deposit_id,
            )
            db.session.add(obj)
        logger.info('Created new Flow %s', obj)
        return obj


class Flow(FlowWrapper):
    """Flow controller class."""

    def __init__(self, deposit_id=None, name='AVCWorkflow',
                 payload=None, user_id=None, model=None):
        """Initialize the flow object."""
        if model:
            self.model = model
        else:
            assert all((deposit_id, payload, user_id))
            bucket_id = payload.get('bucket_id')
            if not bucket_id:
                from cds.modules.deposit.api import deposit_video_resolver
                bucket_id = deposit_video_resolver(deposit_id).files.bucket
                payload.update({"bucket_id": str(bucket_id)})
            self.model = Flow.create(name, deposit_id, payload, user_id)

        self._tasks_map = {
            'file_video_metadata_extraction': ExtractMetadataTask,
            'file_download': DownloadTask,
            'file_transcode': TranscodeVideoTask,
            'file_video_extract_frames': ExtractFramesTask,
        }
        self._tasks = []
        # celery tasks "canvas", holds celery task with passed params,
        # ready to be started
        self._canvas = []

    def _new_task(self, task, create_task_table, kwargs, previous):
        """Create a new task associate with the flow."""
        task_id = uuid()
        kwargs = kwargs if kwargs else {}
        kwargs.update(dict(flow_id=str(self.id), task_id=task_id))
        kwargs.update(self.payload)
        kwargs.pop("flow", None)

        # signature wraps the arguments, keyword arguments, and execution
        # options of a single task invocation
        # Task is a function definition wrapped with decorator,
        # subtask is a task with parameters passed, but not yet started
        #
        # immutable sets the task to take no additional arguments
        # which allows to block the arguments sharing alongside the task chain
        signature = task.subtask(
            task_id=task_id,
            kwargs=kwargs,
            immutable=True,
        )

        if create_task_table:
            TaskModel.create(
                id_=task_id,
                flow_id=str(self.id),
                name=task.name,
                previous=previous,
                payload=kwargs,
            )

        return signature

    def create_task(self, task_name, create_task_table=True, **kwargs):
        """Create a task with parameters from flow."""
        payload = deepcopy(self.payload)
        payload.update(**kwargs)
        return self._tasks_map[task_name](), payload, create_task_table

    def clean_task(self, task_name, *args, **kwargs):
        """Clean a task."""
        kwargs['version_id'] = self.payload['version_id']
        kwargs['deposit_id'] = self.payload['deposit_id']
        return self._tasks_map[task_name]().clean(*args, **kwargs)

    def build_steps(self):
        """Build flow's tasks.

        self._tasks = [(metadata_extraction, task_kwargs), <-- Step 1
                        [                                  <-- Step 2 runs next
        (frame_extraction, task_kwargs), (transcoding1, task_kwargs)<--parallel
                        ]
        ]
        """

        # First step
        has_remote_file_to_download = self.payload.get('uri')
        has_user_uploaded_file = self.payload.get('version_id')

        metadata_extraction_task = self.create_task(
            task_name='file_video_metadata_extraction')

        if has_user_uploaded_file and not has_remote_file_to_download:

            self._tasks.append(metadata_extraction_task)
        else:
            file_download_task = self.create_task(task_name='file_download')

            parallel_tasks = [metadata_extraction_task, file_download_task]

            self._tasks.append(parallel_tasks)

        # Second step
        all_distinct_qualities = get_all_distinct_qualities()

        # create tasks in parallel
        parallel_tasks_group = []
        video_extract_task = self.create_task(
            task_name='file_video_extract_frames'
        )
        parallel_tasks_group.append(video_extract_task)
        transcode_task = self.create_task(
            flow=self, task_name='file_transcode', create_task_table=False
        )
        parallel_tasks_group.append(transcode_task)

        self._tasks.append(parallel_tasks_group)

    def assemble(self):
        """Build the canvas out of the task list."""
        if self.model is None:
            raise RuntimeError('No database flow object found.')
        if self.model.tasks:
            raise RuntimeError(
                'This flow instance was already assembled, use create'
                'to create a new instance and restart the flow.'
            )
        self.build_steps()

        previous = []
        for obj in self._tasks:

            is_single_task = isinstance(obj, tuple)
            is_group_of_tasks = isinstance(obj, list)

            if is_single_task:
                task, kwargs, create_task_table = obj
                signature = self._new_task(
                    task, create_task_table, kwargs, previous=previous
                )
                self._canvas.append(signature)
                previous = [signature.id]
            elif is_group_of_tasks:
                sub_canvas = [
                    self._new_task(
                        t, create_task_table, t_kwargs, previous=previous
                    )
                    for t, t_kwargs, create_task_table in obj
                ]
                previous = [t.id for t in sub_canvas]
                self._canvas.append(celery_group(sub_canvas, task_id=uuid()))
            else:
                raise RuntimeError(
                    'Error while parsing the task list %s', self._tasks
                )
        db.session.commit()
        self._canvas = celery_chain(*self._canvas, task_id=str(self.id))

        return self

    def start(self):
        """Start the flow asynchronously."""
        if not self._canvas:
            self.assemble()
        return self._canvas.apply_async()

    def run(self):
        """Run workflow for video transcoding.

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
          * :func: `~cds.modules.flows.tasks.DownloadTask`
          * :func: `~cds.modules.flows.tasks.ExtractMetadataTask`
          * :func: `~cds.modules.flows.tasks.ExtractFramesTask`
          * :func: `~cds.modules.flows.tasks.TranscodeVideoTask`
        """
        deposit_id = self.deposit_id
        flow_id = self.id
        has_remote_file_to_download = self.payload.get('uri')
        has_user_uploaded_file = self.payload.get('version_id')
        has_file = has_remote_file_to_download or has_user_uploaded_file
        has_deposit = deposit_id
        has_filename = self.payload.get('key')

        assert has_deposit
        assert has_file
        assert has_filename

        # 1. create the object version if doesn't exist
        object_version = init_object_version(self)
        version_id = str(object_version.version_id)
        self.payload['version_id'] = version_id
        flag_modified(self.model, "payload")
        db.session.commit()

        # 2. define the workflow and run
        self.start()
        db.session.commit()
        flow = Flow.get_flow(flow_id)
        # 3. update deposit state
        if deposit_id:
            update_deposit_state(deposit_id=deposit_id)
        return flow

    def delete(self):
        """Mark the flow as deleted."""
        self.clean()
        self.deleted = True
        db.session.commit()

    @staticmethod
    def delete_task(task_id):
        """Revoke a specific task."""
        AsyncResult(task_id).revoke(terminate=True)

    def restart_task(self, task_id):
        Task.restart_task(task_id, str(self.id), flow_payload=self.payload)

    def stop(self):
        """Stop the flow."""
        for task in self.model.tasks:
            Task().stop_task(task)

    def clean(self):
        """Delete tasks and everything created by them."""
        self.clean_task(task_name='file_video_extract_frames')
        for preset_quality in get_all_distinct_qualities():
            self.clean_task(
                task_name='file_transcode',
                preset_quality=preset_quality,
            )
        self.clean_task(task_name='file_video_metadata_extraction')
        if not self.payload.get('version_id'):
            self.clean_task(task_name='file_download')

        # stop the workflow
        self.stop()
