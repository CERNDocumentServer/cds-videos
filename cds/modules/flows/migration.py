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
from invenio_files_rest.models import ObjectVersionTag, as_object_version
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from cds.modules.deposit.api import Video
from cds.modules.flows.models import FlowMetadata, FlowTaskMetadata, FlowTaskStatus
from cds.modules.flows.tasks import (
    ExtractFramesTask,
    ExtractMetadataTask,
    TranscodeVideoTask,
)
from cds.modules.opencast.utils import can_be_transcoded, find_lowest_quality
from cds.modules.records.api import CDSVideosFilesIterator
from cds.modules.records.utils import is_project_record


class MasterFileNotFoundError(Exception):
    """Custom exception when a deposit doesn't have a master file attached."""


class EmptyCDSStateError(Exception):
    """Custom exception when a deposit has an empty `_cds.state`."""


def migrate_event(deposit, logger):
    """Migrate an old event into Flows."""
    # Update flow task status depending on the content of th record

    deposit_id = deposit["_deposit"]["id"]
    user_id = deposit["_deposit"]["created_by"]

    original_file = CDSVideosFilesIterator.get_master_video_file(deposit)
    if not original_file:
        raise MasterFileNotFoundError
    if not deposit.get('_cds', {}).get('state'):
        raise EmptyCDSStateError
    has_metadata = "extracted_metadata" in deposit.get("_cds", {})
    has_frames = bool(CDSVideosFilesIterator.get_video_frames(original_file))
    subformats = CDSVideosFilesIterator.get_video_subformats(original_file)
    payload = dict(
        version_id=original_file["version_id"],
        key=original_file["key"],
        bucket_id=deposit["_buckets"]["deposit"],
        deposit_id=deposit_id,
    )

    logger.debug("Creating Flow for deposit {0} with payload:".format(deposit_id))
    logger.debug(payload)
    flow = FlowMetadata.create(deposit_id=deposit_id, user_id=user_id, payload=payload)
    logger.debug("Flow {0} created successfully for deposit {1}".format(str(flow.id), deposit_id))

    # Create the object tag for flow_id
    object_version = as_object_version(original_file["version_id"])
    logger.debug("Creating ObjectVersionTag for object version bucket_id {0} with flow id {1}:".format(
        object_version.bucket_id, str(flow.id)))
    ObjectVersionTag.create_or_update(object_version, "flow_id", str(flow.id))
    logger.debug("ObjectVersionTag created successfully for flow {0}".format(str(flow.id)))

    subformat_done = [
        f.get("tags", {}).get("preset_quality", "") for f in subformats
    ]
    missing_subformats = [
        s
        for s in set(current_app.config["CDS_OPENCAST_QUALITIES"].keys())
        - set(subformat_done)
        if can_be_transcoded(
            s,
            int(original_file["tags"]["width"]),
            int(original_file["tags"]["height"]),
        )
    ]

    with db.session.begin_nested():
        # add ExtractMetadataTask
        payload["flow_id"] = str(flow.id)

        logger.debug("Creating ExtractMetadataTask for flow {0} and deposit {1} with payload:".format(payload["flow_id"], deposit_id))
        logger.debug(payload)
        metadata_task = FlowTaskMetadata.create(
            flow_id=str(flow.id),
            name=ExtractMetadataTask.name,
            payload=payload,
        )
        logger.debug("ExtractMetadataTask created successfully for flow {0} and deposit {1}".format(payload["flow_id"], deposit_id))

        metadata_task.status = (
            FlowTaskStatus.SUCCESS if has_metadata else FlowTaskStatus.FAILURE
        )
        logger.debug("Updating ExtractMetadataTask status to {}".format(metadata_task.status))
        db.session.add(metadata_task)

        # add ExtractFramesTask
        logger.debug("Creating ExtractFramesTask for flow {0} and deposit {1} with payload:".format(payload["flow_id"], deposit_id))
        logger.debug(payload)
        frames_task = FlowTaskMetadata.create(
            flow_id=str(flow.id), name=ExtractFramesTask.name, payload=payload
        )

        frames_task.status = FlowTaskStatus.SUCCESS if has_frames else FlowTaskStatus.FAILURE
        logger.debug("Updating ExtractFramesTask status to {0}".format(frames_task.status))
        db.session.add(frames_task)

        # add TranscodeVideoTask
        subformats_to_be_processed = subformat_done + missing_subformats
        if not subformats_to_be_processed:
            # If there are no subformats to be processed, it means that there
            # are no subformats done and while checking for the missing ones
            # the lowest quality is not transcodable, in this case add lowest
            subformats_to_be_processed = [find_lowest_quality()]
        for subformat in subformats_to_be_processed:
            subformat_payload = payload.copy()
            subformat_payload.update({"preset_quality": subformat})
            logger.debug("Creating TranscodeVideoTask for flow {0} and deposit {1} with payload:".format(payload["flow_id"], deposit_id))
            logger.debug(subformat_payload)
            transcode_task = FlowTaskMetadata.create(
                flow_id=str(flow.id),
                name=TranscodeVideoTask.name,
                payload=subformat_payload,
            )
            logger.debug("TranscodeVideoTask created successfully for flow {0} and deposit {1}".format(payload["flow_id"], deposit_id))
            transcode_task.status = (
                FlowTaskStatus.FAILURE
                if subformat in missing_subformats
                else FlowTaskStatus.SUCCESS
            )
            logger.debug("Updating TranscodeVideoTask status to {0}".format(transcode_task.status))
            transcode_task.message = (
                "Missing subformat during migration"
                if subformat in missing_subformats
                else "Subformat migrated successfully"
            )
            logger.debug("Updating TranscodeVideoTask message to {0}".format(transcode_task.message))

            db.session.add(transcode_task)

    db.session.commit()

    return flow

def get_all_depid_pids():
    """Get all PIDs for the given type.

    :param pid_type: String representing the PID type value, for example 'recid'.
    """
    pids = (
        PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_type == 'depid'
        )
        .filter(PersistentIdentifier.status == PIDStatus.REGISTERED)
        .order_by(PersistentIdentifier.updated.desc())
        .all()
    )
    return pids

def get_all_depid_pids_since(since_last_updated):
    """Get all PIDs for the given type.

    :param pid_type: String representing the PID type value, for example 'recid'.
    """
    pids = (
        PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_type == 'depid'
        )
        .filter(PersistentIdentifier.status == PIDStatus.REGISTERED)
        .filter(PersistentIdentifier.updated >= since_last_updated)

        .all()
    )
    return pids

def get(name, filepath):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    fh = logging.FileHandler(filepath)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)

    return logger


def main():
    """Migrate old video deposits to the new Flows."""

    failed_filepath = "/tmp/failed_migrated_videos_to_new_flows.log"
    error_logger = get("failed_migrated_videos_to_new_flows", failed_filepath)
    logger = get("migrated_videos_to_new_flows", "/tmp/migrated_videos_to_new_flows.log")
    all_deps = get_all_depid_pids()
    video_deps = []
    failed_deps = dict(
        no_record_found=[],
        master_not_found=[],
        empty_cds_state=[],
        other_exceptions=[]
    )

    for dep in all_deps:
        try:
            rec = Video.get_record(dep.object_uuid)
            if not is_project_record(rec):
                video_deps.append(rec)
        except Exception:
            failed_deps["no_record_found"].append(dep.object_uuid)

    total = len(video_deps)
    for index, video in enumerate(video_deps):
        logger.debug("Migrating deposit {0}/{1}".format(index, total))
        try:
            logger.debug("Migrating deposit {0}".format(video.pid))
            migrate_event(video, logger)
            # we need to commit to re-dump files/tags to the record
            # and store `flow_id`
            logger.debug("Updating task status for deposit {0}".format(video.pid))
            video._update_tasks_status()
            logger.debug("Updated task status for deposit {0} to:".format(video.pid))
            logger.debug(video.get('_cds'))

            logger.debug("Redumping files for deposit {0}".format(video.pid))
            video["_files"] = video._get_files_dump()
            logger.debug("Redumped for deposit {0}:".format(video.pid))
            logger.debug(video["_files"])
            video.commit()
            db.session.commit()
            logger.debug(
                "Migrating deposit {0} ended successfully".format(video.pid)
            )
        except MasterFileNotFoundError:
            logger.debug("Migrating deposit {0} failed. No master file found.".format(video.pid))
            failed_deps["master_not_found"].append(video.pid)
        except EmptyCDSStateError:
            logger.debug("Migrating deposit {0} failed. Empty `_cds.state` found.".format(video.pid))
            failed_deps["empty_cds_state"].append(video.pid)
        except Exception:
            logger.debug("Migrating deposit {0} failed".format(video.pid))
            failed_deps["other_exceptions"].append(video.pid)

    if failed_deps:
        error_logger.debug("Failed deposits {0}".format(len(failed_deps)))
        error_logger.debug(failed_deps)
