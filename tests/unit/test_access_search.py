# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Test access control package."""

from __future__ import absolute_import, print_function

import json
from time import sleep

from flask_principal import RoleNeed, identity_loaded
from flask import g, url_for
from flask_principal import RoleNeed, UserNeed
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from invenio_indexer.api import RecordIndexer

from cds.modules.records.search import CERNRecordsSearch


def mock_provides(needs):
    """Mock user provides."""
    g.identity = lambda: None
    g.identity.provides = needs


def test_es_filter(users):
    """Test query filter based on CERN groups."""
    mock_provides([UserNeed('test@test.ch'), RoleNeed('groupX')])
    assert CERNRecordsSearch().to_dict()['query']['bool']['filter'] == [
        {'bool': {'filter': [{'bool': {
            'should': [
                {'missing': {'field': '_access.read'}},
                {'terms': {'_access.read': ['test@test.ch', 'groupX']}},
                {'terms': {'_access.update': ['test@test.ch', 'groupX']}},
                {'match': {'_deposit.created_by': 0}}
            ]
        }}]}}
    ]


def test_deposit_search(deposit_rest, db, es, users, project, json_headers):
    """Test deposit filters and access rights."""
    RecordIndexer().bulk_index([r.id for r in project])
    RecordIndexer().process_bulk_queue()
    sleep(2)

    with deposit_rest.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        url = url_for('invenio_deposit_rest.project_list', q='')
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 1

    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed(User.query.get(users[1]).email)])

    with deposit_rest.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        url = url_for('invenio_deposit_rest.project_list', q='')
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 0

        # Add user2 as editor for this deposit
        proj = project[0]
        proj['_access'] = {'update': [User.query.get(users[1]).email]}
        proj.commit()
        RecordIndexer().index(proj)
        sleep(2)

        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 1

    # Admin always has access
    @identity_loaded.connect
    def mock_identity_provides_superadmin(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed('superuser')])

    with deposit_rest.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[2]).email)
        url = url_for('invenio_deposit_rest.project_list', q='')
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 1
