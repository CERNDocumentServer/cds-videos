# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Deposit API."""

from __future__ import absolute_import, print_function

from flask import current_app
from invenio_pidstore.models import PersistentIdentifier
from invenio_indexer.api import RecordIndexer
from werkzeug.local import LocalProxy
from invenio_deposit.receivers import \
    index_deposit_after_publish as original_index_deposit_after_publish

from .api import Project
from .tasks import datacite_register


current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def index_deposit_after_publish(sender, action=None, pid=None, deposit=None):
    """Index the record after publishing."""
    project_schema = current_jsonschemas.path_to_url(Project._schema)
    if deposit['$schema'] == project_schema:
        if action == 'publish':
            # index videos (records)
            pid_values = Project(data=deposit).video_ids
            ids = [str(p.object_uuid)
                   for p in PersistentIdentifier.query.filter(
                PersistentIdentifier.pid_value.in_(pid_values)).all()]
            # index project (record)
            _, record = deposit.fetch_published()
            ids.append(str(record.id))
            RecordIndexer().bulk_index(iter(ids))
    else:
        original_index_deposit_after_publish(sender=sender, action=action,
                                             pid=pid, deposit=deposit)


def datacite_register_after_publish(sender, action=None, pid=None,
                                    deposit=None):
    """Mind DOI with DataCite after the deposit has been published."""
    if action == "publish" and \
            current_app.config['DEPOSIT_DATACITE_MINTING_ENABLED']:
        recid_pid, record = deposit.fetch_published()
        datacite_register.delay(recid_pid.pid_value, str(record.id))
