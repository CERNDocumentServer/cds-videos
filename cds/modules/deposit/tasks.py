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


from datetime import datetime, timedelta

from celery import shared_task
from flask import current_app
from invenio_cache import current_cache
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.models import PIDStatus
from invenio_pidstore.providers.datacite import DataCiteProvider
from invenio_records.models import RecordMetadata
from invenio_records_files.api import Record

from ...modules.records.minters import is_local_doi
from ...modules.records.serializers import datacite_v41
from .api import Project


@shared_task(
    bind=True,
    ignore_result=True,
    rate_limit="100/m",
    default_retry_delay=10 * 60,
)
def datacite_register(self, pid_value, record_uuid, max_retries=5, countdown=5):
    """Mint the DOI with DataCite.

    :param pid_value: Value of record PID, with pid_type='recid'.
    :type pid_value: str
    """
    try:
        record = Record.get_record(record_uuid)
        if not record.get("doi"):
            # If it's a project, there is no reserved DOI
            return
        # Bail out if not a CDS DOI.
        if (
            not is_local_doi(record["doi"])
            or not current_app.config["DEPOSIT_DATACITE_MINTING_ENABLED"]
        ):
            return

        dcp = DataCiteProvider.get(record["doi"])

        url = current_app.config["CDS_RECORDS_UI_LINKS_FORMAT"].format(recid=pid_value)

        # check if language field is one of zh_CN or zh_TW and convert it to zh
        # this is needed because datacite 3.0 is supporting only ISO_639-1 codes
        lang = record.get("language")
        if lang and lang in ["zh_CN", "zh_TW"]:
            record["language"] = "zh"
        doc = datacite_v41.serialize(dcp.pid, record)

        if dcp.pid.status == PIDStatus.REGISTERED:
            dcp.update(url, doc)
        else:
            dcp.register(url, doc)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=exc)


@shared_task(ignore_result=True, rate_limit="100/m")
def index_deposit_projects(start_date=None):
    cache = current_cache.get("task_index_deposit_projects:details") or {}
    if "update_date" not in cache:
        # Set the update date by default to 10 minutes ago
        cache["update_date"] = datetime.utcnow() - timedelta(minutes=10)

    start_date = start_date or cache["update_date"]
    records = RecordMetadata.query.filter(
        RecordMetadata.updated > start_date
    ).with_entities(RecordMetadata.id, RecordMetadata.json)

    projects_ids = []
    for _id, json in records:
        if json and json.get("$schema") == current_jsonschemas.path_to_url(
            Project._schema
        ):
            projects_ids.append(str(_id))

    if projects_ids:
        RecordIndexer().bulk_index(iter(projects_ids))

    cache["update_date"] = datetime.utcnow()
    current_cache.set("task_index_deposit_projects:details", cache, timeout=-1)
