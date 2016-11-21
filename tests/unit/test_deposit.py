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

from cds.modules.deposit.api import CDSDeposit, video_resolver
from cds.modules.deposit.permissions import can_edit_deposit
from cds.modules.deposit.views import to_links_js
from flask import current_app, g, request, url_for
from flask_login import login_user
from flask_principal import Identity
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from invenio_db import db
from celery import chain, states, group
from cds.modules.webhooks.receivers import CeleryAsyncReceiver, \
    _info_extractor, _compute_status
from invenio_webhooks import current_webhooks
from helpers import simple_add, failing_task, success_task
from sqlalchemy.orm.attributes import flag_modified

from cds.modules.deposit.loaders import project_loader, video_loader
from cds.modules.deposit.loaders.loader import MarshmallowErrors


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


def test_deposit_events_on_download(api_app, db, depid, bucket, access_token,
                                    json_headers):
    """Test deposit events."""
    db.session.add(bucket)
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            api_app.test_client() as client:
        file_size = 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'content': b'\x00' * file_size,
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            bucket_id=str(bucket.id),
            deposit_id=depid,
            key='test.pdf')

        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 202

        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 202

        video = video_resolver([depid])[0]
        events = video._events

        assert len(events) == 2
        assert events[0].payload['deposit_id'] == depid
        assert events[1].payload['deposit_id'] == depid

        status = video._compute_tasks_status()
        assert status == {'download': states.STARTED}

        # check if the states are inside the deposit
        res = client.get(
            url_for('invenio_deposit_rest.depid_item', pid_value=depid,
                    access_token=access_token),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))['metadata']
        assert data['_deposit']['state']['download'] == states.STARTED


def test_deposit_events_on_worlflow(api_app, db, depid, bucket, access_token,
                                    json_headers):
    """Test deposit events."""
    class TestReceiver(CeleryAsyncReceiver):
        def run(self, event):
            workflow = chain(
                simple_add.s(1, 2),
                group(failing_task.s(), success_task.s())
            )
            self._serialize_result(
                event, workflow.apply_async())
            event.payload['deposit_id'] = depid
            flag_modified(event, 'payload')

        def _status_and_info(self, event, fun=_info_extractor):
            result = self._deserialize_result(event)
            status = _compute_status([
                result.parent.status,
                result.children[0].status,
                result.children[1].status
            ])
            info = fun(result.parent, 'add', [
                fun(result.children[0], 'failing'),
                fun(result.children[1], 'failing')
            ])
            return dict(status=status, info=info)

    receiver_id = 'add-receiver'
    current_webhooks.register(receiver_id, TestReceiver)
    db.session.add(bucket)

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id=receiver_id,
            access_token=access_token)

    with api_app.test_client() as client:
        # run workflow
        resp = client.post(url, headers=json_headers, data=json.dumps({}))
        assert resp.status_code == 500
        # run again workflow
        resp = client.post(url, headers=json_headers, data=json.dumps({}))
        assert resp.status_code == 500
        # resolve deposit and events
        # TODO use a deposit resolver
        video = video_resolver([depid])[0]
        events = video._events
        # check events
        assert len(events) == 2
        assert events[0].payload['deposit_id'] == depid
        assert events[1].payload['deposit_id'] == depid
        # check computed status
        status = video._compute_tasks_status()
        assert status['add'] == states.PENDING
        assert status['failing'] == states.FAILURE

        # check every task for every event
        for event in events:
            result = event.receiver._deserialize_result(event)
            assert result.parent.status == states.PENDING
            assert result.children[0].status == states.FAILURE
            assert result.children[1].status == states.SUCCESS

        # check if the states are inside the deposit
        res = client.get(
            url_for('invenio_deposit_rest.depid_item', pid_value=depid,
                    access_token=access_token),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))['metadata']
        assert data['_deposit']['state']['add'] == states.PENDING
        assert data['_deposit']['state']['failing'] == states.FAILURE
