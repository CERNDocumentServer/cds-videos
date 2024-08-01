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
"""Deposit search tests."""

import json

from flask import url_for
from flask_security import login_user
from helpers import new_project
from invenio_accounts.models import User
from invenio_indexer.api import RecordIndexer
from invenio_search import current_search_client


def test_aggregations(api_app, es, users, location, db, deposit_metadata, json_headers):
    """Test deposit search aggregations."""
    project_1, _, _ = new_project(api_app, users, db, deposit_metadata)
    _users = [users[1]]
    project_2, _, _ = new_project(api_app, _users, db, deposit_metadata)

    RecordIndexer().bulk_index([project_1.id, project_2.id])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        login_user(User.query.get(users[0]))
        url = url_for("invenio_deposit_rest.project_list", q="")
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["aggregations"]["created_by"]["buckets"]) == 1
        assert data["aggregations"]["created_by"]["buckets"][0]["key"] == users[0]

        # Invalid query syntax (Invalid ES syntax)
        url = url_for("invenio_deposit_rest.project_list")
        res = client.get(url, headers=json_headers, query_string=dict(q="title/back"))
        assert res.status_code == 400
