# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
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

"""Test cds package."""

from __future__ import absolute_import, print_function

import json

import mock
import pytest
from flask import current_app, g, request, url_for
from flask_login import login_user
from flask_principal import Identity
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from invenio_db import db
from invenio_files_rest.models import Bucket
from invenio_records.models import RecordMetadata
from invenio_records_files.api import RecordsBuckets

from cds.modules.deposit.api import CDSDeposit
from cds.modules.deposit.links import deposit_links_factory
from cds.modules.deposit.loaders import project_loader, video_loader
from cds.modules.deposit.loaders.loader import MarshmallowErrors
from cds.modules.deposit.permissions import can_edit_deposit
from cds.modules.deposit.views import to_links_js


def test_deposit_link_factory_has_bucket(app, db, es, users, location,
                                         cds_jsonresolver, json_headers,
                                         deposit_rest, project_metadata):
    """Test bucket link factory retrieval of a bucket."""
    with app.test_client() as client:
        login_user_via_session(client, email=users[0].email)

        # Test links for project
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_metadata), headers=json_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        links = data['links']
        pid = data['metadata']['_deposit']['id']
        assert 'bucket' in links
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid,
        )

        # Test links for videos
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps({
                '_project_id': pid,
            }), headers=json_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        links = data['links']
        pid = data['metadata']['_deposit']['id']
        assert 'bucket' in links
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid,
        )

        # Test links for general deposits
        res = client.post(
            url_for('invenio_deposit_rest.depid_list'),
            data=json.dumps({}), headers=json_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        links = data['links']
        pid = data['metadata']['_deposit']['id']
        assert 'bucket' in links
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid,
        )


def test_cds_deposit(es, location):
    """Test CDS deposit creation."""
    deposit = CDSDeposit.create({})
    assert '_buckets' in deposit


def test_links_filter(es, location):
    """Test Jinja to_links_js filter."""
    assert to_links_js(None) == []
    deposit = CDSDeposit.create({})
    links = to_links_js(deposit.pid, deposit)
    assert all([key in links for key in ['self', 'edit', 'publish', 'bucket',
               'files', 'html', 'discard']])
    self_url = links['self']
    assert links['discard'] == self_url + '/actions/discard'
    assert links['edit'] == self_url + '/actions/edit'
    assert links['publish'] == self_url + '/actions/publish'
    assert links['files'] == self_url + '/files'


def test_permissions(es, location):
    """Test deposit permissions."""
    deposit = CDSDeposit.create({})
    deposit.commit()
    user = User(email='user@cds.cern', password='123456', active=True)
    g.identity = Identity(user.id)
    db.session.add(user)
    db.session.commit()
    login_user(user, force=True)
    assert not can_edit_deposit(deposit)
    deposit['_deposit']['owners'].append(user.id)
    assert can_edit_deposit(deposit)


def test_validation_missing_fields(es, location):
    """Test validation error due to missing fields."""
    project_deposit = dict(contributors=[{}], _deposit={'id': None})
    with current_app.test_request_context(
        '/api/deposits/project', method='PUT',
            data=json.dumps(project_deposit), content_type='application/json'):
            with pytest.raises(MarshmallowErrors) as errors:
                project_loader()
            assert '400: Bad Request' in str(errors.value)

            error_body = json.loads(errors.value.get_body())
            assert error_body['status'] == 400
            assert error_body['errors'][0]['field'] == 'contributors.0.name'

    project_deposit['contributors'][0]['name'] = 'Jack'
    with current_app.test_request_context(
        '/api/deposits/project', method='PUT',
            data=json.dumps(project_deposit), content_type='application/json'):
            loaded = project_loader()
            assert 'contributors' in loaded and '_deposit' in loaded


def test_validation_unknown_fields(es, location):
    """Test validation error due to unknown fields."""
    json_data = json.dumps({'desc': {}, '_deposit': {'id': None}})
    with current_app.test_request_context(
        '/api/deposits/video', method='PUT',
            data=json_data, content_type='application/json'):
        with pytest.raises(MarshmallowErrors) as errors:
            video_loader()
        assert '400: Bad Request' in str(errors.value)

        error_body = json.loads(errors.value.get_body())
        assert error_body['status'] == 400
        assert error_body['errors'][0]['field'] == 'desc'
