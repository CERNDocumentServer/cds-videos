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

import random
import string

import mock
import copy
import json

import os
import pytest

from time import sleep

import arrow
from flask_principal import RoleNeed, identity_loaded
from flask_security import login_user
from invenio_db import db
from celery.exceptions import Retry
from flask import url_for
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag, \
    FileInstance
from invenio_pidstore.providers.recordid import RecordIdProvider
from helpers import prepare_videos_for_publish
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from invenio_indexer.api import RecordIndexer
from cds.modules.deposit.api import deposit_video_resolver, \
    deposit_project_resolver
from cds.modules.deposit.receivers import datacite_register_after_publish
from cds.modules.deposit.tasks import datacite_register
from six import BytesIO


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_registering_the_datacite(
        datacite_mock, api_app, users, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata):
    """Test video publish registering the datacite."""
    # test: enable datacite registration
    api_app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ CREATE NEW PROJECT ]]
        project_dict = _create_new_project(client,
                                           json_partial_project_headers,
                                           project_deposit_metadata)

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_1_dict = _add_video_info_to_project(client,
                                                  json_partial_video_headers,
                                                  project_dict,
                                                  video_deposit_metadata)

        video_1_depid = video_1_dict['metadata']['_deposit']['id']
        video_1 = deposit_video_resolver(video_1_depid)
        prepare_videos_for_publish([video_1])

        # [[ PUBLISH VIDEO ]]
        video_1.publish()

        # [[ REGISTER DATACITE ]]
        datacite_register_after_publish(
            sender=api_app, action='publish', deposit=video_1)

        assert datacite_mock.called is True
        assert datacite_mock().metadata_post.call_count == 1
        datacite_mock().doi_post.assert_called_once_with(
            '10.0000/cds.1', 'https://cds.cern.ch/record/1')

        # [[ UPDATE DATACITE ]]
        datacite_register_after_publish(
            sender=api_app, action='publish', deposit=video_1)

        assert datacite_mock.called is True
        assert datacite_mock().metadata_post.call_count == 2
        datacite_mock().doi_post.assert_called_with(
            '10.0000/cds.1', 'https://cds.cern.ch/record/1')


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_registering_the_datacite_if_fail(
        datacite_mock, api_app, users, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata):
    """Test video publish registering the datacite."""
    # test: enable datacite registration
    api_app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ CREATE NEW PROJECT ]]
        project_dict = _create_new_project(client,
                                           json_partial_project_headers,
                                           project_deposit_metadata)

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_1_dict = _add_video_info_to_project(client,
                                                  json_partial_video_headers,
                                                  project_dict,
                                                  video_deposit_metadata)
        video_1_depid = video_1_dict['metadata']['_deposit']['id']
        video_1 = deposit_video_resolver(video_1_depid)
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
        datacite_mock, api_app, users, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata,
        keyword_1, keyword_2):
    """Test video publish registering the datacite not local."""
    # test: enable datacite registration
    api_app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        project_deposit_metadata['keywords'] = [copy.deepcopy(keyword_2)]

        # [[ CREATE NEW PROJECT ]]
        project_dict = _create_new_project(client,
                                           json_partial_project_headers,
                                           project_deposit_metadata)

        assert project_dict['metadata']['keywords'][0] == keyword_2
        project_depid = project_dict['metadata']['_deposit']['id']
        project = deposit_project_resolver(project_depid)
        assert project['keywords'] == [{
            '$ref': keyword_2.ref,
            'name': keyword_2['name'],
        }]

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
        video_1 = deposit_video_resolver(video_1_depid)
        assert video_1['keywords'] == [{
            '$ref': keyword_1.ref,
            'name': keyword_1['name'],
        }]
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


@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_access_rights_based_on_user_id(
        mock_datacite, api_app, users, api_project):
    """Test video access rights based on user ID.

    Tests that a user can't access a deposit created by a different user.
    """
    (project, video_1, video_2) = api_project
    cds_depid = video_1['_deposit']['id']
    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        deposit_url = url_for('invenio_deposit_rest.video_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.video_actions',
                              pid_value=cds_depid, action='publish')
        # check anonymous don't have access
        assert client.get(deposit_url).status_code == 401
        assert client.post(publish_url).status_code == 401
        # User is the creator of the deposit, so everything is fine
        login_user_via_session(client, email=User.query.get(users[0]).email)
        assert client.get(deposit_url).status_code == 200
        assert client.post(publish_url).status_code == 202

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        publish_url = url_for('invenio_deposit_rest.video_actions',
                              pid_value=cds_depid, action='publish')
        deposit_url = url_for('invenio_deposit_rest.video_item',
                              pid_value=cds_depid)
        # User shouldn't have access to this deposit
        assert client.get(deposit_url).status_code == 403
        assert client.post(publish_url).status_code == 403


@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_access_rights_based_on_egroup(
        mock_datacite, api_app, users, api_project):
    """Test video access rights based on the e-groups.

    Tests that a user can access a deposit based on the e-group permissions.
    """
    (project, video_1, video_2) = api_project
    cds_depid = video_1['_deposit']['id']

    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed('test-egroup@cern.ch')])

    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        video_1['_access'] = {'update': ['test-egroup@cern.ch']}
        video_1.commit()
        db.session.commit()
        login_user_via_session(client,
                               email=User.query.get(users[1]).email)
        deposit_url = url_for('invenio_deposit_rest.video_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.video_actions',
                              pid_value=cds_depid, action='publish')
        assert client.get(deposit_url).status_code == 200
        assert client.post(publish_url).status_code == 202


@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_access_rights_based_admin(
        mock_datacite, api_app, users, api_project):
    """Test video access rights based on the admin."""
    (project, video_1, video_2) = api_project
    cds_depid = video_1['_deposit']['id']
    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        login_user_via_session(client,
                               email=User.query.get(users[2]).email)
        deposit_url = url_for('invenio_deposit_rest.video_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.video_actions',
                              pid_value=cds_depid, action='publish')
        assert client.get(deposit_url).status_code == 200
        assert client.post(publish_url).status_code == 202


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_video_publish_edit_publish_again(
        datacite_mock, es, api_app, users, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, video_deposit_metadata, project_deposit_metadata):
    """Test video publish registering the datacite not local."""
    # test: enable datacite registration
    api_app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = True
    api_app.config['PIDSTORE_DATACITE_DOI_PREFIX'] = '10.5072'

    with api_app.test_request_context():
        with api_app.test_client() as client:
            login_user_via_session(client,
                                   email=User.query.get(users[0]).email)

            # [[ CREATE A NEW PROJECT ]]
            project_dict = _create_new_project(client,
                                               json_partial_project_headers,
                                               project_deposit_metadata)

            # [[ ADD A NEW EMPTY VIDEO_1 ]]
            video_1_dict = _add_video_info_to_project(
                client, json_partial_video_headers, project_dict,
                video_deposit_metadata)

            video_1_depid = video_1_dict['metadata']['_deposit']['id']
            video_1 = deposit_video_resolver(video_1_depid)
            prepare_videos_for_publish([video_1])

            # [[ PUBLISH VIDEO ]]
            _deposit_publish(client, json_headers, video_1['_deposit']['id'])

            datacite_register.s(
                pid_value='123', record_uuid=str(video_1.id)).apply()

            # [[ EDIT VIDEO ]]
            _deposit_edit(client, json_headers, video_1['_deposit']['id'])

            # [[ MODIFY DOI -> SAVE ]]
            video_1 = deposit_video_resolver(video_1_depid)
            video_1_dict = copy.deepcopy(video_1)
            #  old_doi = video_1_dict['doi']
            video_1_dict['doi'] = '10.1123/doi'
            del video_1_dict['_files']
            res = client.put(
                url_for('invenio_deposit_rest.video_item',
                        pid_value=video_1['_deposit']['id']),
                data=json.dumps(video_1_dict),
                headers=json_headers)
            # check returned value
            assert res.status_code == 400
            data = json.loads(res.data.decode('utf-8'))
            assert data['errors'] == [
                {"field": "doi",
                 "message": "The DOI cannot be changed."}
            ]

            video_1 = deposit_video_resolver(video_1_depid)
            #  video_1['doi'] = old_doi
            video_1_dict = copy.deepcopy(video_1)
            del video_1_dict['_files']
            # try to modify preserved fields
            video_1_dict['recid'] = 12323233
            video_1_dict['report_number'] = ['fuuu barrrr']
            video_1_dict['publication_date'] = '2000-12-03'
            video_1_dict['_project_id'] = '1234567'
            # do the call
            res = client.put(
                url_for('invenio_deposit_rest.video_item',
                        pid_value=video_1['_deposit']['id']),
                data=json.dumps(video_1_dict),
                headers=json_headers)
            # check returned value
            assert res.status_code == 200
            # check preserved fields
            video_1_new = deposit_video_resolver(video_1_depid)
            assert video_1_new['recid'] == video_1['recid']
            assert video_1_new['report_number'] == video_1['report_number']
            assert video_1_new[
                'publication_date'] == video_1['publication_date']
            assert video_1_new['_project_id'] == video_1['_project_id']

            # [[ PUBLISH VIDEO ]]
            _deposit_publish(client, json_headers, video_1['_deposit']['id'])

            # check indexed record
            RecordIndexer().process_bulk_queue()
            sleep(2)
            res = client.get(url_for('invenio_records_rest.recid_list',
                                     headers=json_headers))
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            for hit in data['hits']['hits']:
                assert isinstance(hit['id'], int)


@mock.patch('invenio_pidstore.providers.datacite.DataCiteMDSClient')
def test_record_video_links(datacite_mock, api_app, es, api_project, users,
                            json_headers):
    """Test record video links."""
    (project, video_1, video_2) = api_project
    user = User.query.filter_by(id=users[0]).first()
    prepare_videos_for_publish([video_1, video_2])
    vid = video_1['_deposit']['id']
    pid = project['_deposit']['id']

    with api_app.test_client() as client:
        login_user_via_session(client, user)

        # publish video
        url = url_for('invenio_deposit_rest.video_actions',
                      pid_value=vid, action='publish')
        assert client.post(url).status_code == 202
        rec_pid, rec_video = deposit_video_resolver(vid).fetch_published()

        # get a record video (with no published project)
        url = url_for('invenio_records_rest.recid_item',
                      pid_value=rec_pid.pid_value, _external=True)
        url_prj_edit = 'http://localhost/deposit/project/{0}'.format(pid)
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200

        # check video record
        data = json.loads(res.data.decode('utf-8'))
        assert data['links'] == {
            'self': url,
            'project_edit': url_prj_edit,
        }

        # publish the project
        url = url_for('invenio_deposit_rest.project_actions',
                      pid_value=pid, action='publish')
        assert client.post(url).status_code == 202
        rec_pid_proj, rec_proj = video_1.project.fetch_published()

        # get a record video (with published project)
        url = url_for('invenio_records_rest.recid_item',
                      pid_value=rec_pid.pid_value, _external=True)
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200

        # check video record
        data = json.loads(res.data.decode('utf-8'))
        url_api_prj = 'http://localhost/record/3'
        url_prj = 'http://localhost/record/3'
        assert data['links'] == {
            'self': url,
            'project': url_api_prj,
            'project_html': url_prj,
            'project_edit': url_prj_edit,
        }


@pytest.mark.skip(reason='Review when EOS FUSE is stable enough')
def test_video_publish_symlinks(location, api_project, api_app, users):
    """Test video publish creates symlinks."""
    def _random_string():
        return ''.join(random.choice(string.ascii_uppercase)
                       for _ in range(10))

    def _get_symlink_path(record, filename):
        year = str(arrow.get(record['date']).year)

        base_no_last, _ = os.path.split(location.uri)
        links_location = os.path.join(base_no_last, 'links')

        return os.path.join(links_location, record['type'],
                            record['category'], year,
                            record['report_number'][0],
                            filename)

    def _upload_video_and_publish(video):
        bucket_id = video['_buckets']['deposit']

        random_file_content = 'fake video file ' + _random_string()
        random_bytes = random_file_content.encode('utf-8')
        video_file = ObjectVersion.create(bucket=bucket_id, key='master.mp4',
                                          stream=BytesIO(random_bytes))
        ObjectVersionTag.create(video_file, 'context_type', 'master')

        prepare_videos_for_publish([video])
        published_video = video.publish()
        (_, record_published_video) = published_video.fetch_published()
        return published_video, record_published_video

    def _get_master_file(record):
        master_file = None
        for _file in record.get('_files', []):
            if _file['context_type'] == 'master':
                master_file = _file
        return master_file

    def _verify_file_and_symlink(record, file_id, filename):
        # verify uploaded file exists
        uploaded_file = FileInstance.get(file_id)
        uploaded_file_path = uploaded_file.uri
        assert os.path.exists(uploaded_file_path)

        # verify symlink exists
        symlink_path = _get_symlink_path(record, filename)
        assert os.path.exists(symlink_path)

        # verify symlink points to the correct file
        assert os.path.realpath(symlink_path) == os.path.realpath(
            uploaded_file_path)

    with api_app.test_request_context():
        login_user(User.query.get(users[0]))

        (project, video_1, _) = api_project
        published_video, record = _upload_video_and_publish(video_1)
        assert len(record['_files']) == 1

        master_file = _get_master_file(record)

        _verify_file_and_symlink(record, master_file['file_id'],
                                 master_file['key'])

        # edit published video by uploading a new file and re-publishing
        deposit_video = published_video.edit()
        published_video, record = _upload_video_and_publish(deposit_video)
        assert len(record['_files']) == 1

        master_file = _get_master_file(record)

        _verify_file_and_symlink(record, master_file['file_id'],
                                 master_file['key'])


def _deposit_edit(client, json_headers, id):
    """Post action to edit deposit."""
    res = client.post(
        url_for('invenio_deposit_rest.video_actions',
                pid_value=id, action='edit'),
        headers=json_headers)
    assert res.status_code == 201


def _deposit_publish(client, json_headers, id):
    """Post action to publish deposit."""
    res = client.post(
        url_for('invenio_deposit_rest.video_actions',
                pid_value=id, action='publish'),
        headers=json_headers)
    assert res.status_code == 202


def _add_video_info_to_project(client, json_partial_video_headers,
                               project_dict, video_deposit_metadata):
    """Post video information to add it to the project."""
    video_metadata = copy.deepcopy(video_deposit_metadata)
    video_metadata.update(
        _project_id=project_dict['metadata']['_deposit']['id'])
    res = client.post(
        url_for('invenio_deposit_rest.video_list'),
        data=json.dumps(video_metadata),
        headers=json_partial_video_headers)
    assert res.status_code == 201
    video_1_dict = json.loads(res.data.decode('utf-8'))
    return video_1_dict


def _create_new_project(client, json_partial_project_headers,
                        project_deposit_metadata):
    """Post project info to create a project."""
    res = client.post(
        url_for('invenio_deposit_rest.project_list'),
        data=json.dumps(project_deposit_metadata),
        headers=json_partial_project_headers)
    assert res.status_code == 201
    project_dict = json.loads(res.data.decode('utf-8'))
    return project_dict
