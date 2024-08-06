# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018, 2020 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""A module for common maintenance scripts."""


from flask import current_app
from invenio_db import db

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.records.api import CDSVideosFilesIterator
from cds.modules.records.resolver import record_resolver

from ..flows.api import FlowService
from ..flows.deposit import index_deposit_project
from ..flows.models import FlowMetadata
from ..flows.tasks import TranscodeVideoTask
from ..opencast.utils import can_be_transcoded

id_types = ["recid", "depid"]


def create_all_missing_subformats(id_type, id_value):
    """Create all missing subformats."""
    _validate(id_type=id_type)

    depid, video_deposit = _resolve_deposit(id_type, id_value)
    master, w, h = _get_master_video(video_deposit)
    subformats = CDSVideosFilesIterator.get_video_subformats(master)
    dones = [subformat["tags"]["preset_quality"] for subformat in subformats]
    missing = set(current_app.config["CDS_OPENCAST_QUALITIES"].keys()) - set(dones)
    transcodables_qualities = list(
        filter(
            lambda q: can_be_transcoded(q, w, h),
            missing,
        )
    )

    flow_metadata = FlowMetadata.get_by_deposit(depid)
    assert flow_metadata, "Cannot find Flow for given deposit id {0}".format(depid)

    if transcodables_qualities:
        _run_transcoding_for(flow_metadata, transcodables_qualities)
    return transcodables_qualities


def create_subformat(id_type, id_value, quality):
    """Recreate a given subformat."""
    _validate(id_type=id_type, quality=quality)

    depid, video_deposit = _resolve_deposit(id_type, id_value)
    master, w, h = _get_master_video(video_deposit)

    subformat = can_be_transcoded(quality, w, h)
    if subformat:
        flow_metadata = FlowMetadata.get_by_deposit(depid)
        assert flow_metadata, "Cannot find Flow for given deposit id {0}".format(depid)

        _run_transcoding_for(flow_metadata, [quality])

    return subformat["preset_quality"] if subformat else None


def create_all_subformats(id_type, id_value):
    """Recreate all subformats."""
    _validate(id_type=id_type)

    depid, video_deposit = _resolve_deposit(id_type, id_value)
    master, w, h = _get_master_video(video_deposit)

    transcodables_qualities = list(
        filter(
            lambda q: can_be_transcoded(q, w, h),
            current_app.config["CDS_OPENCAST_QUALITIES"].keys(),
        )
    )

    flow_metadata = FlowMetadata.get_by_deposit(depid)
    assert flow_metadata, "Cannot find Flow for given deposit id {0}".format(depid)

    _run_transcoding_for(flow_metadata, transcodables_qualities)
    return transcodables_qualities


def _run_transcoding_for(flow_metadata, qualities=None):
    """Run transcoding for the given qualities."""
    payload = flow_metadata.payload
    payload = dict(
        deposit_id=payload["deposit_id"],
        flow_id=payload["flow_id"],
        bucket_id=payload["bucket_id"],
        key=payload["key"],
        version_id=payload["version_id"],
    )

    TranscodeVideoTask.create_flow_tasks(payload, qualities=qualities)
    db.session.commit()

    TranscodeVideoTask().s(**payload).apply_async()

    db.session.commit()
    index_deposit_project(payload["deposit_id"])


def _resolve_deposit(id_type, id_value):
    """Return the deposit video."""
    depid = id_value
    if id_type == "recid":
        _, record = record_resolver.resolve(id_value)
        depid = record["_deposit"]["id"]

    return depid, deposit_video_resolver(depid)


def _get_master_video(video_deposit):
    """Return master video."""
    master = CDSVideosFilesIterator.get_master_video_file(video_deposit)
    if not master:
        raise Exception("No master video found for the given record")

    return (
        master,
        int(master["tags"]["width"]),
        int(master["tags"]["height"]),
    )


def _validate(id_type=None, quality=None):
    """Validate input parameters."""
    if id_type not in id_types:
        raise Exception("`id_type` param must be one of {0}".format(id_types))

    all_possible_qualities = current_app.config["CDS_OPENCAST_QUALITIES"].keys()
    if quality and quality not in all_possible_qualities:
        raise Exception(
            "`quality` param must be one of {0}".format(all_possible_qualities)
        )
