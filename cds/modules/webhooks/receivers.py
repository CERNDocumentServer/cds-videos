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

"""Webhook Receivers"""

from __future__ import absolute_import, division

from celery import chain, group
from celery.result import AsyncResult
from invenio_webhooks import Receiver
from .tasks import attach_files, download, extract_metadata, extract_frames, \
    transcode


class TaskReceiver(Receiver):
    """Receiver that runs a long-running task and keeps track of its status."""

    def run(self, event):
        """Run the requested action."""
        action = event.payload['action']
        task_id = event.payload['task_id']
        response = dict(message='Invalid action')

        if action == 'new_task':
            kwargs = event.payload['kwargs']
            tid = self.new_task(task_id, kwargs=kwargs)
            assert tid == task_id
            response['message'] = 'Started task [{}]'.format(task_id)

        elif action == 'get_state':
            (state, meta) = self.get_status(task_id)
            response = dict(state=state, **meta)

        elif action == 'cancel_task':
            message = self.cancel_task(task_id)
            response['message'] = message

        event.response_code = 200
        event.response = response

    def new_task(self, task_id, kwargs):
        raise NotImplemented()

    def get_status(self, task_id):
        raise NotImplemented()

    def cancel_task(self, task_id):
        raise NotImplemented()


class CeleryTaskReceiver(TaskReceiver):
    """Base class for Celery-based TaskReceivers.
    Implementing this class requires the definition of a single Celery task.
    .. note::
        Arguments of the task must match the ones of the task provided exactly.
    """

    @property
    def celery_task(self):
        """Celery task to be executed by this receiver."""
        raise NotImplementedError

    def new_task(self, task_id, kwargs):
        """Start asynchronous execution of Celery task."""
        return self.celery_task.apply_async(task_id=task_id, kwargs=kwargs).id

    def get_status(self, task_id):
        """Retrieve status of current task from the Celery backend."""
        result = AsyncResult(task_id)
        return result.state, result.info if result.state == 'PROGRESS' else {}

    def cancel_task(self, task_id):
        """Cancel execution of the Celery task."""
        AsyncResult(task_id).revoke(terminate=True)
        return 'Revoked task'


class CeleryChainTaskReceiver(TaskReceiver):
    """TaskReceiver specialized for Celery."""

    # List of tuples of the form (celery_task, argument identifiers)
    @property
    def celery_tasks(self):
        raise NotImplemented()

    def new_task(self, task_id, kwargs):
        """Construct Celery canvas.

        This is achieved by chaining sequential tasks and grouping
        concurrent ones.
        """
        task_list = []
        parent_kw = {'parent_id': task_id}
        for task_definition in self.celery_tasks:
            if isinstance(task_definition, tuple):
                task, task_kw = task_definition
                kw = {k: kwargs[k] for k in kwargs if k in task_kw}
                kw.update(parent_kw)
                task_list.append(task.subtask(kwargs=kw))
            elif isinstance(task_definition, list):
                subtasks = []
                for task, task_kw in task_definition:
                    kw = {k: kwargs[k] for k in kwargs if k in task_kw}
                    kw.update(parent_kw)
                    subtasks.append(task.subtask(kwargs=kw))
                task_list.append(group(*subtasks))
        return chain(*task_list, task_id=task_id)().id

    def get_status(self, task_id):
        result = AsyncResult(task_id)
        if result.state in ['PROGRESS', 'EXCEPTION']:
            return result.state, result.info
        else:
            return {}

    def cancel_task(self, task_id):
        AsyncResult(task_id).revoke(terminate=True)
        return 'Revoked task'


class AVWorkflow(CeleryChainTaskReceiver):
    """Composite CeleryChainTaskReceiver for the AV workflow."""

    celery_tasks = [
        (download, {'url', 'bucket_id', 'chunk_size', 'key'}),
        [
            (transcode, {'preset_name'}),
            (extract_frames, {
                'start_percentage', 'end_percentage', 'number_of_frames',
                'size_percentage', 'output_folder'
            })
        ],
        (attach_files, {'bucket_id', 'key'}),
    ]


class VideoMetadataExtractor(CeleryTaskReceiver):
    """Receiver that extracts metadata from video URLs."""

    celery_task = extract_metadata

