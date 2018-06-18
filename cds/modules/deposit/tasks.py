# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Deposit tasks."""

from __future__ import absolute_import, print_function

from invenio_db import db
from flask import current_app
from celery import shared_task
from invenio_indexer.api import RecordIndexer
from invenio_records_files.api import Record
from invenio_pidstore.models import PIDStatus
from invenio_pidstore.providers.datacite import DataCiteProvider
from invenio_jsonschemas import current_jsonschemas

from .api import Video, Project
from .search import AllDraftDepositsSearch
from ...modules.records.serializers import datacite_v31
from ...modules.records.minters import is_local_doi


@shared_task(bind=True, ignore_result=True, rate_limit='100/m',
             default_retry_delay=10 * 60)
def datacite_register(
        self, pid_value, record_uuid, max_retries=5, countdown=5):
    """Mint the DOI with DataCite.

    :param pid_value: Value of record PID, with pid_type='recid'.
    :type pid_value: str
    """
    try:
        record = Record.get_record(record_uuid)
        if not record.get('doi'):
            # If it's a project, there is no reserved DOI
            return
        # Bail out if not a CDS DOI.
        if not is_local_doi(record['doi']) or \
                not current_app.config['DEPOSIT_DATACITE_MINTING_ENABLED']:
            return

        dcp = DataCiteProvider.get(record['doi'])

        url = current_app.config['CDS_RECORDS_UI_LINKS_FORMAT'].format(
            recid=pid_value)
        doc = datacite_v31.serialize(dcp.pid, record)

        if dcp.pid.status == PIDStatus.REGISTERED:
            dcp.update(url, doc)
        else:
            dcp.register(url, doc)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=exc)


def _is_state_changed(record, deposit):
    """Return True if the celery tasks state changed."""
    state_r = record['_cds'].get('state', {})
    state_d = deposit['_cds'].get('state', {})
    return state_r != state_d


def _get_deposits_split_by_type(query):
    """Get video/projects and both as records."""
    video_schema = current_jsonschemas.path_to_url(Video._schema)
    project_schema = current_jsonschemas.path_to_url(Project._schema)
    # get list of videos, project and both as records
    video_ids = []
    project_ids = []
    record_ids = []
    for data in query.scan():
        if data['$schema'] == project_schema:
            project_ids.append(data.meta.id)
        if data['$schema'] == video_schema:
            video_ids.append(data.meta.id)
        record_ids.append(data.meta.id)
    records = {r.id: r for r in Record.get_records(record_ids)}
    projects = Project.get_records(project_ids)
    videos = Video.get_records(video_ids)
    return (videos, projects, records)


@shared_task(ignore_result=True, rate_limit='100/m',
             default_retry_delay=10 * 60)
def preserve_celery_states_on_db():
    """Preserve in db the celery tasks state."""
    (videos, projects, records) = _get_deposits_split_by_type(
        query=AllDraftDepositsSearch())
    ids = []
    # commit only the ones who should be update
    for video in videos:
        if _is_state_changed(records[video.id], video):
            video.commit()
            ids.append(str(video.id))
    for project in projects:
        if _is_state_changed(records[project.id], project):
            project.commit()
            ids.append(str(project.id))
    db.session.commit()
    if ids:
        RecordIndexer().bulk_index(iter(ids))
