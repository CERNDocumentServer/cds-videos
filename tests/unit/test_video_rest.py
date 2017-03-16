# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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

"""Test Deposit video REST."""

from __future__ import absolute_import, print_function

import mock
import copy
import json
import pytest

from invenio_db import db
from celery.exceptions import Retry
from flask import url_for
from invenio_pidstore.providers.recordid import RecordIdProvider
from helpers import prepare_videos_for_publish
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from cds.modules.deposit.api import video_resolver, project_resolver
from cds.modules.deposit.receivers import datacite_register_after_publish
from cds.modules.deposit.tasks import datacite_register


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_registering_the_datacite(
        datacite_mock, app, users, deposit_rest, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata):
    """Test video publish registering the datacite."""
    # test: enable datacite registration
    app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ CREATE NEW PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)

        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_metadata = copy.deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        assert res.status_code == 201
        video_1_dict = json.loads(res.data.decode('utf-8'))
        video_1_depid = video_1_dict['metadata']['_deposit']['id']
        [video_1] = video_resolver([video_1_depid])
        prepare_videos_for_publish([video_1])

        # [[ PUBLISH VIDEO ]]
        video_1.publish()

        # [[ REGISTER DATACITE ]]
        datacite_register_after_publish(
            sender=app, action='publish', deposit=video_1)

        assert datacite_mock.called is True
        assert datacite_mock().metadata_post.call_count == 1
        datacite_mock().doi_post.assert_called_once_with(
            '10.0000/cds.1', 'https://cds.cern.ch/record/1')

        # [[ UPDATE DATACITE ]]
        datacite_register_after_publish(
            sender=app, action='publish', deposit=video_1)

        assert datacite_mock.called is True
        assert datacite_mock().metadata_post.call_count == 2
        datacite_mock().doi_post.assert_called_with(
            '10.0000/cds.1', 'https://cds.cern.ch/record/1')


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_registering_the_datacite_if_fail(
        datacite_mock, app, users, deposit_rest, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata):
    """Test video publish registering the datacite."""
    # test: enable datacite registration
    app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ CREATE NEW PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)

        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_metadata = copy.deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        assert res.status_code == 201
        video_1_dict = json.loads(res.data.decode('utf-8'))
        video_1_depid = video_1_dict['metadata']['_deposit']['id']
        [video_1] = video_resolver([video_1_depid])
        prepare_videos_for_publish([video_1])

        # [[ PUBLISH VIDEO ]]
        video_1.publish()
        db.session.commit()
        with mock.patch(
                'invenio_records.api.Record.get_record',
                side_effect=[Exception, video_1], return_value=video_1):
            with pytest.raises(Retry):
                datacite_register.s(
                    pid_value='1', record_uuid=str(video_1.id)).apply()

        assert datacite_mock.called is True
        assert datacite_mock().metadata_post.call_count == 1
        datacite_mock().doi_post.assert_called_once_with(
            '10.0000/cds.1', 'https://cds.cern.ch/record/1')
        assert datacite_mock.call_count == 3


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_registering_the_datacite_not_local(
        datacite_mock, app, users, deposit_rest, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata,
        keyword_1, keyword_2):
    """Test video publish registering the datacite not local."""
    # test: enable datacite registration
    app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        project_deposit_metadata['keywords'] = [copy.deepcopy(keyword_2)]

        # [[ CREATE NEW PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)

        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['keywords'][0] == keyword_2
        project_depid = project_dict['metadata']['_deposit']['id']
        project = project_resolver(project_depid)
        assert project['keywords'] == [{'$ref': keyword_2.ref}]

        # [[ ADD A NEW VIDEO_1 ]]
        video_metadata = copy.deepcopy(video_deposit_metadata)
        video_metadata['keywords'] = [copy.deepcopy(keyword_1)]
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        assert res.status_code == 201
        video_1_dict = json.loads(res.data.decode('utf-8'))
        assert video_1_dict['metadata']['keywords'][0] == keyword_1
        video_1_depid = video_1_dict['metadata']['_deposit']['id']
        [video_1] = video_resolver([video_1_depid])
        assert video_1['keywords'] == [{'$ref': keyword_1.ref}]
        video_1['doi'] = '10.1123/doi'
        prepare_videos_for_publish([video_1])

        # [[ PUBLISH VIDEO ]]
        video_1.publish()
        datacite_register.s(
            pid_value='123', record_uuid=str(video_1.id)).apply()

        assert datacite_mock.called is False


def test_video_keywords_serializer(api_app, es, api_project, keyword_1,
                                   keyword_2, users, json_headers):
    """Tet video keywords serializer."""
    (project, video_1, video_2) = api_project
    # login owner
    user = User.query.filter_by(id=users[0]).first()

    assert video_1['keywords'] == []

    # try to add keywords
    video_1.add_keyword(keyword_1)
    video_1.add_keyword(keyword_2)
    video_1.commit()

    # check serializer
    with api_app.test_client() as client:
        login_user_via_session(client, user)

        vid = video_1['_deposit']['id']
        url = url_for('invenio_deposit_rest.video_item', pid_value=vid)
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200

        # check keywords
        data = json.loads(res.data.decode('utf-8'))
        kw_result = {k['key_id']: k['name']
                     for k in data['metadata']['keywords']}
        kw_expect = {k['key_id']: k['name'] for k in [keyword_1, keyword_2]}
        assert kw_expect == kw_result
