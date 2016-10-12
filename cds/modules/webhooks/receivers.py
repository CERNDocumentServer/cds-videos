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

from invenio_webhooks.models import CeleryReceiver
from .tasks import attach_files, download, extract_metadata, extract_frames, \
    transcode, chain_orchestrator


class CeleryChainReceiver(CeleryReceiver):
    """CeleryReceiver specialized for multi-task workflows."""

    @property
    def workflow(self):
        raise NotImplemented()

    def run(self, event):
        """Construct Celery canvas.

        This is achieved by chaining sequential tasks and grouping
        concurrent ones.
        """
        chain_orchestrator.apply(
            (self.workflow, ), kwargs=event.payload, task_id=event.id)


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
        (attach_files, {'bucket_id', 'key'}),
    ]


class Downloader(CeleryReceiver):
    """Receiver that downloads data from a URL."""

    def run(self, event):
        """Execute download task."""
        download.apply_async(kwargs=event.payload)


class VideoMetadataExtractor(CeleryReceiver):
    """Receiver that extracts metadata from video URLs."""

    def run(self, event):
        """Execute extract_metadata task."""
        extract_metadata.apply_async(kwargs=event.payload)
        pass

