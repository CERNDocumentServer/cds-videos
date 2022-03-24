# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2018 CERN.
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

"""CDS Deposit receivers."""

from __future__ import absolute_import, print_function

from flask import current_app
from invenio_db import db
from invenio_jsonschemas import current_jsonschemas

from cds.modules.deposit.api import record_unbuild_url
from cds.modules.flows.tasks import (DownloadTask, ExtractFramesTask,
                                     ExtractMetadataTask, TranscodeVideoTask)
from cds.modules.records.resolver import record_resolver

from .api import Project
from .indexer import CDSRecordIndexer
from .tasks import datacite_register


def index_deposit_after_action(sender, action=None, pid=None, deposit=None):
    """Index the record after publishing."""
    CDSRecordIndexer().index(deposit, action)


def update_project_id_after_publish(sender, action=None, pid=None,
                                    deposit=None):
    """Update the project id for each video on publish."""
    if action != "publish":
        return

    project_schema = current_jsonschemas.path_to_url(Project._schema)
    is_project = deposit.get("$schema") == project_schema
    if not is_project:
        return

    # project is published after any other video
    for video_ref in deposit._video_refs:
        pid, video = record_resolver.resolve(record_unbuild_url(video_ref))
        if video["_project_id"] != str(deposit["recid"]):
            video["_project_id"] = str(deposit["recid"])
            video.commit()

    db.session.commit()


def datacite_register_after_publish(
    sender, action=None, pid=None, deposit=None
):
    """Mind DOI with DataCite after the deposit has been published."""
    if (
        action == "publish"
        and current_app.config["DEPOSIT_DATACITE_MINTING_ENABLED"]
    ):
        recid_pid, record = deposit.fetch_published()

        if record.get("doi"):
            datacite_register.delay(recid_pid.pid_value, str(record.id))


def register_celery_class_based_tasks(sender, app=None):
    """Register class based celery tasks as they cannot be autodiscovered.

    Celery 4 doesn't autodiscover class based celery tasks thus we need to
    register them explicitly.
    """
    celery = app.extensions["invenio-celery"].celery
    celery.tasks.register(ExtractMetadataTask())
    celery.tasks.register(DownloadTask())
    celery.tasks.register(ExtractFramesTask())
    celery.tasks.register(TranscodeVideoTask())
