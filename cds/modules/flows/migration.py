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

"""Flow migration helper functions."""

from invenio_db import db

from ..deposit.api import deposit_video_resolver
from ..records.api import CDSVideosFilesIterator
from .models import Status


def migrate_event(event):
    """Migrate an old event into Flows."""
    receiver = event.receiver
    flow = receiver._workflow(event=event)

    # Update flow task status depending on the content of th record
    deposit_id = event.payload['deposit_id']
    deposit = deposit_video_resolver(deposit_id)

    original_file = CDSVideosFilesIterator.get_master_video_file(deposit)
    has_metadata = 'extracted_metadata' in deposit.get('_cds', {})
    has_frames = bool(CDSVideosFilesIterator.get_video_frames(original_file))
    presets_present = [
        f.get('tags, {}').get('preset_quality', '')
        for f in CDSVideosFilesIterator.get_video_subformats(original_file)
    ]

    with db.session.begin_nested():
        for task in flow.model.tasks:
            if 'DownloadTask' in task.name:
                task.status = Status.SUCCESS
            elif 'ExtractFramesTask' in task.name:
                task.status = Status.SUCCESS if has_frames else Status.PENDING
            elif 'ExtractMetadataTask' in task.name:
                task.status = (
                    Status.SUCCESS if has_metadata else Status.PENDING
                )
            elif 'TranscodeVideoTask' in task.name:
                task.status = (
                    Status.SUCCESS
                    if task.payload.get('preset_quality') in presets_present
                    else Status.PENDING
                )
            db.session.add(task)
    db.session.commit()

    return flow
