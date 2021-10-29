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

import logging

from flask import current_app
from invenio_db import db
from invenio_files_rest.models import (
    ObjectVersionTag,
    as_object_version,
)
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from cds.modules.records.utils import is_project_record
from cds.modules.deposit.api import CDSDeposit

from ..opencast.utils import can_be_transcoded
from ..records.api import CDSVideosFilesIterator
from .api import Flow, uuid
from .models import Status, TaskMetadata


def migrate_event(deposit):
    """Migrate an old event into Flows."""
    # Update flow task status depending on the content of th record

    deposit_id = deposit["_deposit"]["id"]
    user_id = deposit["_deposit"]["created_by"]

    original_file = CDSVideosFilesIterator.get_master_video_file(deposit)
    if not original_file:

        return
    has_metadata = 'extracted_metadata' in deposit.get('_cds', {})
    has_frames = bool(CDSVideosFilesIterator.get_video_frames(original_file))
    subformats = CDSVideosFilesIterator.get_video_subformats(original_file)
    payload = dict(
        version_id=original_file["version_id"],
        key=original_file["key"],
        bucket_id=deposit['_buckets']['deposit'],
        deposit_id=deposit_id
    )

    flow = Flow(
        deposit_id=deposit_id,
        user_id=user_id,
        payload=payload
    )

    # Create the object tag for _flow_id
    object_version = as_object_version(original_file["version_id"])
    ObjectVersionTag.create_or_update(
            object_version, '_flow_id', str(flow.id)
        )

    subformat_done = [
        f.get('tags', {}).get('preset_quality', '') for f in subformats
    ]
    missing_subformats = [
        s
        for s in set(current_app.config['CDS_OPENCAST_QUALITIES'].keys()) - set(subformat_done)
        if can_be_transcoded(
            s,
            int(original_file['tags']['width']),
            int(original_file['tags']['height']),
        )
    ]

    with db.session.begin_nested():
        # add ExtractMetadataTask
        task_id = uuid()
        payload["flow_id"] = str(flow.id)

        metadata_task = TaskMetadata.create(
            id_=task_id,
            flow_id=str(flow.id),
            name='cds.modules.flows.tasks.ExtractMetadataTask',
            previous=[],
            payload=payload
        )
        metadata_task.status = Status.SUCCESS if has_metadata else Status.FAILURE
        db.session.add(metadata_task)

        # add ExtractFramesTask
        task_id = uuid()

        frames_task = TaskMetadata.create(
            id_=task_id,
            flow_id=str(flow.id),
            name='cds.modules.flows.tasks.ExtractFramesTask',
            previous=[],
            payload=payload
        )

        frames_task.status=Status.SUCCESS if has_frames else Status.FAILURE
        db.session.add(frames_task)

        # add TranscodeVideoTask

        for subformat in subformat_done:
            task_id = uuid()
            transcode_task = TaskMetadata.create(
                id_=task_id,
                flow_id=str(flow.id),
                name='cds.modules.flows.tasks.TranscodeVideoTask',
                previous=[],
                payload=payload
            )
            transcode_task.status=Status.FAILURE if subformat in missing_subformats else Status.SUCCESS
            db.session.add(transcode_task)

    db.session.commit()

    return flow


def main():
    """Migrate old video deposits to the new Flows."""

    def get_all_pids_by(pid_type):
        """Get all PIDs for the given type.

        :param pid_type: String representing the PID type value, for example 'recid'.
        """
        pids = PersistentIdentifier.query.filter(PersistentIdentifier.pid_type == pid_type).filter(
            PersistentIdentifier.status == PIDStatus.REGISTERED).all()
        return pids

    def get(name, filepath):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        fh = logging.FileHandler(filepath)
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        sh.setLevel(logging.DEBUG)
        logger.addHandler(sh)

        return logger

    filepath = '/tmp/failed_migrated_videos_to_new_flows.log'
    logger = get("failed_migrated_videos_to_new_flows", filepath)
    all_deps = get_all_pids_by("depid")
    video_deps = []
    failed_deps = []

    for dep in all_deps:
        rec = CDSDeposit.get_record(dep.object_uuid)
        if not is_project_record(rec):
            video_deps.append(rec)

    for video in video_deps:
        try:
            migrate_event(video)
        except Exception:
            failed_deps.append(video)
        # we need to commit to re-dump files/tags to the record
        # and store `_flow_id`
        video._update_tasks_status()
        video['_files'] = video._get_files_dump()
        video.commit()
    db.session.commit()

    if failed_deps:
        logger.debug("Failed deposits ({0})".format(len(failed_deps)))
        logger.debug(failed_deps)
