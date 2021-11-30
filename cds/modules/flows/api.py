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
from collections import defaultdict

from celery import chain as celery_chain
from celery.result import AsyncResult
from invenio_db import db
from sqlalchemy.orm.attributes import flag_modified as db_flag_modified

from .deposit import index_deposit_project
from .errors import TaskAlreadyRunningError
from .files import init_object_version
from .models import FlowMetadata
from .models import FlowTaskStatus
from .models import as_task
from .tasks import (
    CeleryTask,
    DownloadTask,
    ExtractFramesTask,
    ExtractMetadataTask,
    TranscodeVideoTask,
)

logger = logging.getLogger("cds-flow")


def get_tasks_status_grouped_by_task_name(flow):
    """Get tasks status grouped by task name for a specific flow."""
    results = defaultdict(list)
    for task in flow.tasks:
        results[task.name].append(task.status)

    return {
        k: str(FlowTaskStatus.compute_status(v)) for k, v in results.items() if v
    }


def merge_tasks_status(statuses_1, statuses_2):
    """Merge task statuses."""
    statuses = {}
    task_names = set(statuses_1.keys()) | set(statuses_2.keys())

    for task in task_names:
        task_statuses_values = [statuses_1.get(task), statuses_2.get(task)]
        statuses[task] = str(FlowTaskStatus.compute_status(task_statuses_values))
    return statuses


class AVCFlowCeleryTasks:
    @classmethod
    def create_task(cls, celery_task_cls, payload, **kwargs):
        """Create a task with parameters from flow."""
        _payload = dict()
        _payload.update(payload)
        _payload.update(**kwargs)

        celery_task = celery_task_cls()
        # create TaskMetadata rows
        celery_task.create_flow_tasks(_payload)

        return celery_task, _payload

    @classmethod
    def clean_task(cls, celery_task_cls, payload, *args, **kwargs):
        """Clean a task."""
        kwargs["version_id"] = payload["version_id"]
        kwargs["deposit_id"] = payload["deposit_id"]
        return celery_task_cls().clean(*args, **kwargs)

    @classmethod
    def create_task_signature(cls, celery_task, **kwargs):
        """Create a new Celery task signature for Celery canvas."""
        signature = celery_task.subtask(
            kwargs=kwargs,
            immutable=True,
        )
        return signature

    @classmethod
    def _build_chain(cls, payload):
        """Build flow's tasks."""
        celery_tasks = []

        has_remote_file_to_download = payload.get("uri")
        has_user_uploaded_file = payload.get("version_id")
        if not has_user_uploaded_file and has_remote_file_to_download:
            file_download_task = cls.create_task(DownloadTask, payload)
            celery_tasks.append(file_download_task)

        metadata_extract_task = cls.create_task(ExtractMetadataTask, payload)
        celery_tasks.append(metadata_extract_task)

        frames_extract_task = cls.create_task(ExtractFramesTask, payload)
        celery_tasks.append(frames_extract_task)

        transcode_task = cls.create_task(TranscodeVideoTask, payload)
        celery_tasks.append(transcode_task)

        return celery_tasks

    @classmethod
    def build_workflow(cls, payload):
        """Build the Celery tasks sequence for the workflow."""
        celery_tasks = cls._build_chain(payload)

        celery_tasks_signatures = []
        for celery_task_tuple in celery_tasks:
            assert isinstance(celery_task_tuple, tuple)
            celery_task, kwargs = celery_task_tuple
            signature = cls.create_task_signature(celery_task, **kwargs)
            celery_tasks_signatures.append(signature)

        return celery_chain(*celery_tasks_signatures)


class FlowService:
    """Flow service."""

    def __init__(self, flow_metadata):
        """Constructor."""
        self.flow_metadata = flow_metadata

    def run(self):
        """Run workflow for video transcoding.

        Steps:
          * Download the video file (if not done yet).
          * Extract metadata from the video.
          * Run video transcoding.
          * Extract frames from the video.

        Mandatory fields in the payload:
          * bucket_id
          * key
          * deposit_id
          * version_id or uri: uri if the video has been downloaded via HTTP,
            version_id if the video needs to be downloaded.

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
        flow_id = str(self.flow_metadata.id)
        payload = self.flow_metadata.payload
        payload["flow_id"] = flow_id

        deposit_id = self.flow_metadata.deposit_id
        has_deposit = deposit_id

        has_remote_file_to_download = payload.get("uri", False)
        has_user_uploaded_file = payload.get("version_id", False)
        has_file = has_remote_file_to_download or has_user_uploaded_file
        has_filename = payload["key"]

        assert has_deposit
        assert has_file
        assert has_filename

        # create the object version if doesn't exist
        object_version = init_object_version(self.flow_metadata)
        version_id = str(object_version.version_id)
        payload["version_id"] = version_id
        db_flag_modified(self.flow_metadata, "payload")
        db.session.commit()

        # start the celery tasks for the flow
        celery_tasks = AVCFlowCeleryTasks.build_workflow(payload)
        celery_tasks.apply_async()

        # Flow and Tasks modifications need to be persisted
        db.session.commit()
        index_deposit_project(deposit_id)

    def delete(self):
        """Mark the flow as deleted.

        In reality, we just unmark the flow as the last one associated with
        a specific deposit_id.
        """
        self.clean()
        self.flow_metadata.is_last = False
        db.session.commit()

    @staticmethod
    def delete_task(task_id):
        """Revoke a specific task."""
        AsyncResult(task_id).revoke(terminate=True)

    def run_celery_task(self, celery_task, **kwargs):
        """Run a specific Celery task."""
        self._start_celery_task(celery_task, **kwargs)

    def restart_task(self, task, **kwargs):
        """Restart a specific task"""
        task_metadata = as_task(task)
        if task_metadata.status == FlowTaskStatus.PENDING:
            raise TaskAlreadyRunningError(
                "Task with id {0} is already running.".format(
                    str(task_metadata.id)
                )
            )

        def find_celery_task_by_name(name):
            for celery_task in [
                DownloadTask,
                ExtractMetadataTask,
                ExtractFramesTask,
                TranscodeVideoTask,
            ]:
                if celery_task.name == name:
                    return celery_task
            raise

        celery_task = find_celery_task_by_name(task_metadata.name)
        self._start_celery_task(celery_task, **kwargs)

    def _start_celery_task(self, celery_task, **kwargs):
        """Start a specific celery task."""
        payload = self.flow_metadata.payload
        payload = dict(
            deposit_id=payload["deposit_id"],
            flow_id=payload["flow_id"],
            key=payload["key"],
            version_id=payload["version_id"],
            **kwargs
        )

        celery_task().apply_async(**payload)

    def stop(self):
        """Stop the flow."""
        for task in self.flow_metadata.tasks:
            celery_task_id = task.payload["celery_task_id"]
            CeleryTask.stop_task(celery_task_id)
            task.status = FlowTaskStatus.CANCELLED
        db.session.commit()

    def clean(self):
        """Delete tasks and everything created by them."""
        self.stop()

        payload = self.flow_metadata.payload

        remote_file_was_downloaded = self.flow_metadata.payload.get("uri", False)
        if remote_file_was_downloaded:
            AVCFlowCeleryTasks.clean_task("file_download", **payload)

        AVCFlowCeleryTasks.clean_task(
            "file_video_metadata_extraction", **payload
        )
        AVCFlowCeleryTasks.clean_task("file_video_extract_frames", **payload)
        AVCFlowCeleryTasks.clean_task("file_transcode", **payload)
