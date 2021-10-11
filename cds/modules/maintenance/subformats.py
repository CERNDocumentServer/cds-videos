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

from __future__ import absolute_import, print_function

from cds_sorenson.api import can_be_transcoded, get_all_distinct_qualities
from celery import chain
from invenio_db import db

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.flows.models import Status
from cds.modules.records.api import CDSVideosFilesIterator
from cds.modules.records.resolver import record_resolver
from cds.modules.webhooks.status import get_deposit_flows, get_deposit_last_flow

from .tasks import MaintenanceTranscodeVideoTask

id_types = ['recid', 'depid']


def create_all_missing_subformats(id_type, id_value):
    """Create all missing subformats."""
    _validate(id_type=id_type)

    video_deposit, dep_uuid = _resolve_deposit(id_type, id_value)
    master, ar, w, h = _get_master_video(video_deposit)
    subformats = CDSVideosFilesIterator.get_video_subformats(master)

    dones = [subformat['tags']['preset_quality'] for subformat in subformats]
    missing = set(get_all_distinct_qualities()) - set(dones)
    transcodables = list(
        filter(lambda q: can_be_transcoded(q, ar, w, h), missing)
    )

    # sequential (and immutable) transcoding to avoid MergeConflicts on bucket
    return transcodables, _schedule(dep_uuid, transcodables)


def create_subformat(id_type, id_value, quality):
    """Recreate a given subformat."""
    _validate(id_type=id_type, quality=quality)

    video_deposit, dep_uuid = _resolve_deposit(id_type, id_value)
    master, ar, w, h = _get_master_video(video_deposit)

    subformat = can_be_transcoded(quality, ar, w, h)
    return (
        subformat,
        _schedule(dep_uuid, [subformat.get('quality')]) if subformat else None,
    )


def create_all_subformats(id_type, id_value):
    """Recreate all subformats."""
    _validate(id_type=id_type)

    video_deposit, dep_uuid = _resolve_deposit(id_type, id_value)
    master, ar, w, h = _get_master_video(video_deposit)

    transcodables = list(
        filter(
            lambda q: can_be_transcoded(q, ar, w, h),
            get_all_distinct_qualities(),
        )
    )

    # sequential (and immutable) transcoding to avoid MergeConflicts on bucket
    return transcodables, _schedule(dep_uuid, transcodables)


def _resolve_deposit(id_type, id_value):
    """Return the deposit video."""
    depid = id_value
    if id_type == 'recid':
        _, record = record_resolver.resolve(id_value)
        depid = record['_deposit']['id']

    return deposit_video_resolver(depid), depid


def _get_master_video(video_deposit):
    """Return master video."""
    master = CDSVideosFilesIterator.get_master_video_file(video_deposit)
    if not master:
        raise Exception("No master video found for the given record")

    return (
        master,
        master['tags']['display_aspect_ratio'],
        int(master['tags']['width']),
        int(master['tags']['height']),
    )


def _validate(id_type=None, quality=None):
    """Validate input parameters."""
    if id_type not in id_types:
        raise Exception('`id_type` param must be one of {0}'.format(id_types))

    all_possible_qualities = get_all_distinct_qualities()
    if quality and quality not in all_possible_qualities:
        raise Exception(
            '`quality` param must be one of {0}'.format(all_possible_qualities)
        )


def _schedule(deposit_id, transcodables):
    """Schedule tasks to run as a chain to avoid flooding the queue."""
    if not transcodables:
        return None

    flow = get_deposit_last_flow(deposit_id)

    # Reset all tasks which quality is within transcodables
    tasks = []
    for t in flow.model.tasks:
        if not t.payload.get('preset_quality') in transcodables:
            continue
        t.status = Status.PENDING
        db.session.add(t)
        tasks.append(MaintenanceTranscodeVideoTask().si(**t.payload))
    # Save task changes so they can start from scratch
    db.session.commit()

    return chain(tasks).apply_async()
