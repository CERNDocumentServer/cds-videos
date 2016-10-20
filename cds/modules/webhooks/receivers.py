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

from invenio_db import db
from invenio_webhooks.models import CeleryReceiver
from sqlalchemy.orm.attributes import flag_modified

from .tasks import attach_files, download, extract_metadata, extract_frames, \
    transcode, chain_orchestrator


class CeleryTaskReceiver(CeleryReceiver):
    """CeleryReceiver specialized for single task execution."""

    @property
    def task(self):
        raise NotImplementedError()

    def run(self, event):
        """Execute task."""
        event.response['event_id'] = str(event.id)
        event.response['message'] = self.task.apply(kwargs=event.payload).get()


class CeleryChainReceiver(CeleryReceiver):
    """CeleryReceiver specialized for multi-task workflows."""

    @property
    def workflow(self):
        raise NotImplementedError()

    def __call__(self, event):
        """Construct Celery canvas.

        This is achieved by chaining sequential tasks and grouping
        concurrent ones.
        """
        event_id = str(event.id)
        chain_orchestrator.apply(
            (self.workflow, ),
            kwargs=event.payload,
            task_id=event_id
        )

        with db.session.begin_nested():
            event.response['event_id'] = event_id
            event.response['message'] = 'Started workflow'
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
            db.session.add(event)
        db.session.commit()


class AVCWorkflow(CeleryChainReceiver):
    """CeleryChainReceiver implementation for the AV workflow."""

    workflow = [
        (download, {'url', 'bucket_id', 'chunk_size', 'key'}),
        [
            (transcode, {'preset_name'}),
            (extract_frames, {
                'start_percentage', 'end_percentage', 'number_of_frames',
                'size_percentage', 'output_folder'
            })
        ],
        (attach_files, {'bucket_id'}),
    ]


class Downloader(CeleryTaskReceiver):
    """Receiver that downloads data from a URL."""
    task = download


class VideoMetadataExtractor(CeleryTaskReceiver):
    """Receiver that extracts metadata from video URLs."""
    task = extract_metadata
