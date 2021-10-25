# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2020 CERN.
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

"""Task status manipulation."""

from __future__ import absolute_import, print_function

import json
import sqlalchemy

from copy import deepcopy
from celery import states
from collections import defaultdict

from sqlalchemy import asc

from ..flows.models import Flow as FlowModel, Status as FlowStatus
from ..flows.api import Flow


TASK_NAMES = {
    'cds.modules.flows.tasks.TranscodeVideoTask': 'file_transcode',
    'cds.modules.flows.tasks.ExtractFramesTask':
        'file_video_extract_frames',
    'cds.modules.flows.tasks.ExtractMetadataTask':
        'file_video_metadata_extraction',
    'cds.modules.flows.tasks.DownloadTask': 'file_download',
}


def get_deposit_flows(deposit_id, _deleted=False):
    """Get a list of events associated with a deposit."""
    #  return Event.query.filter(
    #      Event.payload.op('->>')(
    #          'deposit_id').cast(String) == self['_deposit']['id']).all()
    deposit_id = str(deposit_id)
    # do you want to involve deleted events?
    filters = []

    if not _deleted:
        filters.append(FlowModel.deleted != True)
    # build base query
    query = FlowModel.query.filter(FlowModel.deposit_id == deposit_id)
    # execute with more filters
    return query.filter(*filters).all()


def get_deposit_last_flow(deposit_id):
    """Get the last flow associated with a deposit."""
    try:
        # In case of many flows, return the last one
        model = FlowModel.query.filter(
            FlowModel.deposit_id == deposit_id)\
            .order_by(asc(FlowModel.updated))[-1]
        return Flow(model=model)
    except IndexError:
        # There is no Flow,
        # Most likely we are working with an old record: Migrate!
        from ..flows.migration import migrate_event

        return migrate_event(deposit_id)


def get_tasks_status_by_task(flows, statuses=None):
    """Get tasks status grouped by task name."""
    results = defaultdict(list)
    for flow in flows:
        for task in get_deposit_last_flow(flow.deposit_id).json['tasks']:
            results[
                TASK_NAMES.get(task['name'], task['name'].split('.')[-1])
            ].append(task['status'])

    return {
        k: str(FlowStatus.compute_status(v)) for k, v in results.items() if v
    }


def merge_tasks_status(statuses_1, statuses_2):
    """Merge task statuses."""
    statuses = {}
    task_names = set(statuses_1.keys()) | set(statuses_2.keys())

    for task in task_names:
        task_statuses_values = [statuses_1.get(task), statuses_2.get(task)]
        statuses[task] = str(FlowStatus.compute_status(task_statuses_values))
    return statuses
