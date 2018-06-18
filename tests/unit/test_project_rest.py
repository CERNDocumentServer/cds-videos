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

"""Test Deposit Project REST."""

from __future__ import absolute_import, print_function

import json
import mock

from time import sleep
from copy import deepcopy
from cds.modules.deposit.resolver import get_video_pid, \
    get_project_pid
from cds.modules.deposit.api import project_resolver, deposit_video_resolver, \
    deposit_videos_resolver, Project, Video, deposit_project_resolver
from flask_security import current_user, login_user
from flask import url_for
from flask_principal import RoleNeed, UserNeed, identity_loaded
from invenio_db import db
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from invenio_indexer.api import RecordIndexer
from helpers import prepare_videos_for_publish, new_project
from cds.modules.deposit.indexer import CDSRecordIndexer


def test_simple_workflow(
        api_app, db, es, users, location, cds_jsonresolver,
        data_file_1, data_file_2,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        deposit_metadata, project_deposit_metadata, video_deposit_metadata):
    """Test project simple workflow."""
    def check_connection(videos, project):
        """check project <---> video connection."""
        assert all({"$ref": video.ref} in project['videos']
                   for video in videos)
        assert len(videos) == len(project['videos'])

    project_schema = ('https://cdslabs.cern.ch/schemas/'
                      'deposits/records/videos/project/project-v1.0.0.json')
    video_schema = ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/videos/video/video-v1.0.0.json')

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ CREATE NEW PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)

        # check returned value
        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['videos'] == []
        assert project_dict['metadata']['title']['title'] == 'my project'
        assert project_dict['links']['bucket'].startswith(
            'http://localhost/files/')
        assert all(link.startswith('http://localhost/deposits/project')
                   for (key, link) in project_dict['links'].items()

                   if key not in ['html', 'bucket'])
        # check database
        project_id = project_dict['metadata']['_deposit']['id']
        project = project_resolver.resolve(project_id)[1]
        assert project['$schema'] == project_schema

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        # check returned value
        assert res.status_code == 201
        video_1_dict = json.loads(res.data.decode('utf-8'))
        assert video_1_dict['metadata']['_project_id'] == project_id
        assert all(link.startswith('http://localhost/deposits/video')
                   for (key, link) in video_1_dict['links'].items()
                   if key not in ['html', 'bucket'])
        # check database: connection project <---> videos
        video_ids = [
            video_1_dict['metadata']['_deposit']['id']
        ]
        [video_1] = deposit_videos_resolver(video_ids)
        check_connection(
            [video_1],
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )
        assert video_1['$schema'] == video_schema

        # [[ GET THE VIDEO 1 ]]
        res = client.get(
            video_1_dict['links']['self'],
            headers=json_headers)

        # check returned value
        assert res.status_code == 200
        video_1_dict = json.loads(res.data.decode('utf-8'))
        assert video_1_dict['metadata']['_files'] == []

        # [[ ADD A NEW EMPTY VIDEO_2 ]]
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        # check returned value
        assert res.status_code == 201
        video_2_dict = json.loads(res.data.decode('utf-8'))
        assert video_2_dict['metadata']['_project_id'] == project_id
        assert all(link.startswith('http://localhost/deposits/video')
                   for (key, link) in video_2_dict['links'].items()
                   if key not in ['html', 'bucket'])
        # check database: connection project <---> videos
        video_ids = [
            video_1_dict['metadata']['_deposit']['id'],
            video_2_dict['metadata']['_deposit']['id']
        ]
        [video_1, video_2] = deposit_videos_resolver(video_ids)
        check_connection(
            [video_1, video_2],
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )
        assert video_2['$schema'] == video_schema

        # [[ ADD A FILE INSIDE VIDEO_1 ]]
        res = client.post(
            url_for('invenio_deposit_rest.video_files',
                    pid_value=video_1_dict['metadata']['_deposit']['id']),
            data=data_file_1, content_type='multipart/form-data')

        # check returned value
        assert res.status_code == 201
        file_1 = json.loads(res.data.decode('utf-8'))
        assert file_1['checksum'] == 'md5:eb88ae1e3666e6fe96a33ea72aab630e'
        assert file_1['filesize'] == 24
        assert file_1['filename'] == 'test.json'
        assert file_1['id']
        # check database: connection project <---> videos
        video_1 = deposit_video_resolver(
            video_1_dict['metadata']['_deposit']['id'])
        assert video_1['_files'][0]['key'] == 'test.json'
        video_ids = [
            video_1_dict['metadata']['_deposit']['id'],
            video_2_dict['metadata']['_deposit']['id']
        ]
        check_connection(
            deposit_videos_resolver(video_ids),
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )

        # [[ GET THE VIDEO 1 ]]
        res = client.get(video_1_dict['links']['self'], headers=json_headers)

        # check video metadata
        assert res.status_code == 200
        video_1_dict = json.loads(res.data.decode('utf-8'))
        assert len(video_1_dict['metadata']['_files']) == 1
        myfile = video_1_dict['metadata']['_files'][0]
        assert myfile['links']['self'].startswith(
            'https://cdslabs.cern.ch/api/files/')
        assert myfile['checksum'] == 'md5:eb88ae1e3666e6fe96a33ea72aab630e'
        assert myfile['completed'] is True
        assert 'version_id' in myfile
        assert myfile['key'] == 'test.json'
        assert myfile['size'] == 24

        # [[ PUBLISH VIDEO_1 ]]
        # Not need to send _files
        del video_1_dict['metadata']['_files']
        # Prepare video for publishing
        prepare_videos_for_publish([video_1, video_2])
        res = client.post(
            url_for('invenio_deposit_rest.video_actions',
                    pid_value=video_1['_deposit']['id'], action='publish'),
            headers=json_headers)

        # check returned value
        assert res.status_code == 202
        video_1_dict = json.loads(res.data.decode('utf-8'))
        assert video_1_dict['metadata']['_deposit']['status'] == 'published'
        assert video_1_dict['metadata']['recid'] == 1
        assert video_1_dict['metadata']['_project_id'] == project_id
        # check database: connection project <---> videos
        video_ids = [
            video_1_dict['metadata']['_deposit']['id'],
            video_2_dict['metadata']['_deposit']['id']
        ]
        check_connection(
            deposit_videos_resolver(video_ids),
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )

        # [[ ADD A VIDEO INSIDE VIDEO_2 ]]
        res = client.post(
            url_for('invenio_deposit_rest.video_files',
                    pid_value=video_2_dict['metadata']['_deposit']['id']),
            data=data_file_2, content_type='multipart/form-data')

        # check returned value
        assert res.status_code == 201
        file_2 = json.loads(res.data.decode('utf-8'))
        assert file_2['checksum'] == 'md5:95405c14852500dcbb6dbfd9e27a3594'
        assert file_2['filesize'] == 26
        assert file_2['filename'] == 'test2.json'
        # check connection project <---> videos
        video_2 = deposit_video_resolver(
            video_2_dict['metadata']['_deposit']['id'])
        assert video_2['_files'][0]['key'] == 'test2.json'
        video_ids = [
            video_1_dict['metadata']['_deposit']['id'],
            video_2_dict['metadata']['_deposit']['id']
        ]
        check_connection(
            deposit_videos_resolver(video_ids),
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )

        # [[ PUBLISH THE PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=project['_deposit']['id'], action='publish'),
            headers=json_headers)

        def get_video_record(depid):
            deposit = deposit_video_resolver(depid)
            return Video.get_record(deposit.fetch_published()[1].id)

        video_1 = get_video_record(video_1_dict['metadata']['_deposit']['id'])
        video_2 = get_video_record(video_2_dict['metadata']['_deposit']['id'])
        record_videos = [video_1, video_2]

        # check returned value
        assert res.status_code == 202
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['_deposit']['status'] == 'published'
        assert project_dict['metadata']['recid'] == 3
        assert project_dict['metadata']['videos'][0] == record_videos[0]
        assert project_dict['metadata']['videos'][1] == record_videos[1]
        # check database: connection project <---> videos
        check_connection(
            record_videos,
            project_resolver.resolve(
                project_dict['metadata']['_deposit']['id'])[1]
        )

        # check indexed record
        RecordIndexer().process_bulk_queue()
        sleep(2)
        res = client.get(url_for('invenio_records_rest.recid_list',
                                 headers=json_headers))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        for hit in data['hits']['hits']:
            assert isinstance(hit['id'], int)

        # [[ EDIT THE PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=project_dict['metadata']['_deposit']['id'],
                    action='edit'),
            headers=json_headers)

        # check returned value
        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['_deposit']['status'] == 'draft'
        # check database
        project = project_resolver.resolve(
            project_dict['metadata']['_deposit']['id'])[1]
        assert project['_deposit']['status'] == 'draft'

        # [[ MODIFY PROJECT ]]
        project_before = project_resolver.resolve(
            project_dict['metadata']['_deposit']['id'])[1]
        project_dict['metadata']['title']['title'] = 'new project title'
        # Not need to send _files
        del project_dict['metadata']['_files']
        # try to modify preserved fields
        project_dict['metadata']['recid'] = 12323233
        project_dict['metadata']['report_number'][0] = 'fuuu barrrr'
        project_dict['metadata']['publication_date'] = '2000-12-03'
        # do the call
        res = client.put(
            url_for('invenio_deposit_rest.project_item',
                    pid_value=project_dict['metadata']['_deposit']['id']),
            data=json.dumps(project_dict['metadata']),
            headers=json_headers)
        # check returned value
        assert res.status_code == 200
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['title']['title'] ==\
            'new project title'
        assert all(link.startswith('http://localhost/deposits/project')
                   for (key, link) in project_dict['links'].items()
                   if key not in ['html', 'bucket'])
        video_1 = get_video_record(video_1_dict['metadata']['_deposit']['id'])
        video_2 = get_video_record(video_2_dict['metadata']['_deposit']['id'])
        assert video_1 == project_dict['metadata']['videos'][0]
        assert video_2 == project_dict['metadata']['videos'][1]
        # check database
        project = project_resolver.resolve(
            project_dict['metadata']['_deposit']['id'])[1]
        assert project['title']['title'] == 'new project title'
        # check preserved fields
        assert project_before['recid'] == project['recid']
        assert project_before['report_number'] == project['report_number']
        assert project_before[
            'publication_date'] == project['publication_date']

        # [[ DISCARD PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=project_dict['metadata']['_deposit']['id'],
                    action='discard'),
            headers=json_headers)
        # check returned value
        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict['metadata']['title']['title'] == 'my project'
        # check database
        project = project_resolver.resolve(
            project_dict['metadata']['_deposit']['id'])[1]
        assert project['title']['title'] == 'my project'


def test_publish_project_check_indexed(
        api_app, db, es, users, location, cds_jsonresolver,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        video_deposit_metadata, project_deposit_metadata):
    """Test create a project and check project and videos are indexed."""
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ GET EMPTY PROJECT LIST ]]
        res = client.get(
            url_for('invenio_deposit_rest.project_list'),
            headers=json_headers)

        assert res.status_code == 200
        project_list = json.loads(res.data.decode('utf-8'))
        assert project_list['hits']['hits'] == []

        # [[ CREATE NEW PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)

        assert res.status_code == 201
        project_dict = json.loads(res.data.decode('utf-8'))

        # [[ ADD A NEW EMPTY VIDEO_1 ]]
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        # check returned value
        assert res.status_code == 201
        video_1_dict = json.loads(res.data.decode('utf-8'))

        # [[ ADD A NEW EMPTY VIDEO_2 ]]
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(
            _project_id=project_dict['metadata']['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)

        # check returned value
        assert res.status_code == 201
        video_2_dict = json.loads(res.data.decode('utf-8'))

        # get video ids
        video_ids = [
            video_1_dict['metadata']['_deposit']['id'],
            video_2_dict['metadata']['_deposit']['id']
        ]
        [video_1, video_2] = deposit_videos_resolver(video_ids)
        video_1_id = str(video_1.id)
        video_2_id = str(video_2.id)
        # get project id
        project_depid = project_dict['metadata']['_deposit']['id']
        project = project_resolver.resolve(project_depid)[1]
        project_id = str(project.id)
        project = dict(project)

        with mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
                as mock_indexer:
            # [[ PUBLISH THE PROJECT ]]
            prepare_videos_for_publish([video_1, video_2])
            client.post(
                url_for('invenio_deposit_rest.project_actions',
                        pid_value=project['_deposit']['id'], action='publish'),
                headers=json_headers)

            # get project record
            _, project_record = project_resolver.resolve(
                project_depid)[1].fetch_published()
            # get video records
            video_records = Project(data=project_record).videos
            assert len(video_records) == 2
            # check project + videos are indexed. We also index the project
            # deposit on publish, so we have one more id
            assert mock_indexer.called is True
            ids = list(list(mock_indexer.mock_calls[0])[1][0])
            assert len(ids) == 4
            # check video deposit are not indexed
            assert video_1_id not in ids
            assert video_2_id not in ids
            # check project deposit is indexed
            assert project_id in ids
            # check video records are indexed
            assert str(video_records[0].id) in ids
            assert str(video_records[1].id) in ids
            # check project record is indexed
            assert str(project_record.id) in ids


def test_boolean_fields_are_indexed(api_app, es, api_project, users,
                                    json_headers):
    """Test boolean fields (i.e. featured and vr) are indexed."""
    (project, video_1, video_2) = api_project
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # [[ PUBLISH THE PROJECT ]]
        prepare_videos_for_publish([video_1, video_2])
        client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=project['_deposit']['id'], action='publish'),
            headers=json_headers)

        RecordIndexer().process_bulk_queue()
        sleep(2)

        video_1_record = deposit_video_resolver(video_1['_deposit']['id'])
        video_2_record = deposit_video_resolver(video_2['_deposit']['id'])

        def assert_get_video(query, video_record):
            url = url_for('invenio_records_rest.recid_list', q=query)
            res = client.get(url, headers=json_headers)
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert len(data['hits']['hits']) == 1
            assert data['hits']['hits'][0]['id'] == video_record['recid']

        # Featured
        assert_get_video('featured:true', video_1_record)
        # Not featured
        assert_get_video('featured:false', video_2_record)
        # VR
        assert_get_video('vr:true', video_1_record)
        # Not VR
        assert_get_video('vr:false', video_2_record)


def test_project_keywords_serializer(api_app, es, api_project, keyword_1,
                                     keyword_2, users, json_headers):
    """Tet video keywords serializer."""
    (project, video_1, video_2) = api_project
    user = User.query.filter_by(id=users[0]).first()

    assert project['keywords'] == []

    # try to add keywords
    project.add_keyword(keyword_1)
    project.add_keyword(keyword_2)
    project.commit()

    # check serializer
    with api_app.test_client() as client:
        # login owner
        login_user_via_session(client, user)

        pid = project['_deposit']['id']
        url = url_for('invenio_deposit_rest.project_item', pid_value=pid)
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200

        # check keywords
        data = json.loads(res.data.decode('utf-8'))
        kw_result = {k['key_id']: k['name']
                     for k in data['metadata']['keywords']}
        kw_expect = {k['key_id']: k['name'] for k in [keyword_1, keyword_2]}
        assert kw_expect == kw_result


def test_project_access_rights_based_on_user_id(api_app, users, api_project):
    """Test project access rights based on user ID.

    Tests that a user can't access a deposit created by a different user.
    """
    (project, video_1, video_2) = api_project
    cds_depid = project['_deposit']['id']
    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.project_actions',
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
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.project_actions',
                              pid_value=cds_depid, action='publish')
        # User shouldn't have access to this deposit
        assert client.get(deposit_url).status_code == 403
        assert client.post(publish_url).status_code == 403


def test_project_access_rights_based_on_egroup(api_app, users, api_project):
    """Test project access rights based on the e-groups.

    Tests that a user can access a deposit based on the e-group permissions.
    """
    (project, video_1, video_2) = api_project
    cds_depid = project['_deposit']['id']

    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed('test-egroup@cern.ch')])

    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        project['_access'] = {'update': ['test-egroup@cern.ch']}
        project.commit()
        db.session.commit()
        login_user_via_session(client,
                               email=User.query.get(users[1]).email)
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.project_actions',
                              pid_value=cds_depid, action='publish')
        assert client.get(deposit_url).status_code == 200
        assert client.post(publish_url).status_code == 202


def test_project_access_rights_based_admin(api_app, users, api_project):
    """Test project access rights based on the admin."""
    (project, video_1, video_2) = api_project
    cds_depid = project['_deposit']['id']
    with api_app.test_client() as client:
        prepare_videos_for_publish([video_1, video_2])
        login_user_via_session(client,
                               email=User.query.get(users[2]).email)
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        publish_url = url_for('invenio_deposit_rest.project_actions',
                              pid_value=cds_depid, action='publish')
        assert client.get(deposit_url).status_code == 200
        assert client.post(publish_url).status_code == 202


def test_deleted(api_app, db, location, api_project, users, json_headers):
    """Test delete of project/videos."""
    (project, video_1, video_2) = api_project

    def get_vids(project):
        return [video['_deposit']['id'] for video in project['videos']]

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # check project contains both videos
        pid = project['_deposit']['id']
        url = url_for('invenio_deposit_rest.project_item', pid_value=pid)
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        vids = get_vids(data['metadata'])
        assert video_1['_deposit']['id'] in vids
        assert video_2['_deposit']['id'] in vids
        assert len(vids) == 2

        # check pids
        pid = get_project_pid(pid_value=project['_deposit']['id'])
        assert pid.is_deleted() is False
        pid = get_video_pid(pid_value=video_1['_deposit']['id'])
        assert pid.is_deleted() is False
        pid = get_video_pid(pid_value=video_2['_deposit']['id'])
        assert pid.is_deleted() is False

        # delete video_1
        vid = video_1['_deposit']['id']
        url = url_for('invenio_deposit_rest.video_item', pid_value=vid)
        res = client.delete(url, headers=json_headers)
        assert res.status_code == 204

        CDSRecordIndexer().process_bulk_queue()

        # check project contains only video_2
        pid = project['_deposit']['id']
        url = url_for('invenio_deposit_rest.project_item', pid_value=pid)
        res = client.get(url, headers=json_headers)
        data = json.loads(res.data.decode('utf-8'))
        vids = get_vids(data['metadata'])
        assert video_1['_deposit']['id'] not in vids
        assert video_2['_deposit']['id'] in vids
        assert len(vids) == 1

        # check elasticsearch is up-to-date
        sleep(2)
        res = client.get(
            url_for('invenio_deposit_rest.project_list',
                    q='_deposit.id:{0}'.format(pid)),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        vids = get_vids(data['hits']['hits'][0]['metadata'])
        assert video_1['_deposit']['id'] not in vids
        assert video_2['_deposit']['id'] in vids
        assert len(vids) == 1

        # check pids
        pid = get_project_pid(pid_value=project['_deposit']['id'])
        assert pid.is_deleted() is False
        pid = get_video_pid(pid_value=video_1['_deposit']['id'])
        assert pid.is_deleted() is True
        pid = get_video_pid(pid_value=video_2['_deposit']['id'])
        assert pid.is_deleted() is False

        # delete the project
        pid = project['_deposit']['id']
        url = url_for('invenio_deposit_rest.project_item', pid_value=pid)
        res = client.delete(url, headers=json_headers)
        assert res.status_code == 204

        # check elasticsearch is up-to-date
        CDSRecordIndexer().process_bulk_queue()
        sleep(2)
        res = client.get(url_for('invenio_deposit_rest.project_list', q='_deposit.id:{0}'.format(pid)), headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 0

        # check pids
        pid = get_project_pid(pid_value=project['_deposit']['id'])
        assert pid.is_deleted() is True
        pid = get_video_pid(pid_value=video_1['_deposit']['id'])
        assert pid.is_deleted() is True
        pid = get_video_pid(pid_value=video_2['_deposit']['id'])
        assert pid.is_deleted() is True


def test_default_order(api_app, es, cds_jsonresolver, users,
                       location, db, deposit_metadata, json_headers):
    """Test default project order."""
    (project_1, _, _) = new_project(api_app, es, cds_jsonresolver, users,
                                    location, db, deposit_metadata,
                                    project_data={
                                        'title': {'title': 'project 1'}
                                    }, wait=False)
    project_1.commit()
    db.session.commit()
    (project_2, _, _) = new_project(api_app, es, cds_jsonresolver, users,
                                    location, db, deposit_metadata,
                                    project_data={
                                        'title': {'title': 'alpha'}
                                    }, wait=False)
    project_2.commit()
    db.session.commit()
    (project_3, _, _) = new_project(api_app, es, cds_jsonresolver, users,
                                    location, db, deposit_metadata,
                                    project_data={
                                        'title': {'title': 'zeta'}
                                    }, wait=False)
    project_3.commit()
    db.session.commit()
    (project_4, _, _) = new_project(api_app, es, cds_jsonresolver, users,
                                    location, db, deposit_metadata,
                                    project_data={
                                        'title': {'title': 'project 2'}
                                    }, wait=False)
    project_4.commit()
    db.session.commit()
    sleep(2)

    def check_order(data, orders):
        hits = [hit['metadata']['title']['title']
                for hit in data['hits']['hits']]
        assert hits == orders

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # test order: title descending
        res = client.get(
            url_for('invenio_deposit_rest.project_list', sort='-title_desc'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        check_order(data, ['zeta', 'project 2', 'project 1', 'alpha'])

        # test order: title ascending
        res = client.get(
            url_for('invenio_deposit_rest.project_list', sort='title_asc'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        check_order(data, ['alpha', 'project 1', 'project 2', 'zeta'])

        # test order: older first
        res = client.get(
            url_for(
                'invenio_deposit_rest.project_list',
                sort='oldest_created'
            ),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        check_order(data, ['project 1', 'alpha', 'zeta', 'project 2'])

        # test default order: newest first
        res = client.get(
            url_for('invenio_deposit_rest.project_list'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        check_order(data, ['project 2', 'zeta', 'alpha', 'project 1'])


def test_search_excluded_fields(api_app, users, api_project,
                                json_headers, location,
                                project_deposit_metadata):
    """Test search excluded fields."""
    # publish a project with "contributors" field
    (project, video_1, video_2) = api_project
    with api_app.test_request_context():
        prepare_videos_for_publish([video_1, video_2])
        video_1['contributors'] = [
            {
                "affiliations": [
                    "Universita degli Studi di Udine (IT)"
                ],
                "email": "example@cern.ch",
                "ids": [
                    {
                        "source": "cern",
                        "value": "123456"
                    },
                    {
                        "source": "cds",
                        "value": "67890"
                    }
                ],
                "name": "Fuu, Bar",
                "role": "Director"
            }
        ],
        login_user(User.query.get(users[0]))
        project = project.publish()

        video = project.videos[0]
        indexer = RecordIndexer()
        indexer.index(video)
        sleep(2)

    with api_app.test_client() as client:
        # check record is indexed
        res = client.get(url_for('invenio_records_rest.recid_list',
                                 headers=json_headers))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 1

        # check record is not searchable for contributors role
        res = client.get(url_for('invenio_records_rest.recid_list',
                                 q='Director', headers=json_headers))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 0

        # check record is not searchable for contributors id
        res = client.get(url_for('invenio_records_rest.recid_list',
                                 q='67890', headers=json_headers))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 0


def test_aggregations(api_app, es, cds_jsonresolver, users,
                      location, db, deposit_metadata, json_headers):
    """Test default project order."""
    indexer = RecordIndexer()
    # project 1
    (project_1, _, _) = new_project(
        api_app, es, cds_jsonresolver, users,
        location, db, deposit_metadata,
        project_data={
            'title': {'title': 'project 1'},
            'category': 'CERN',
        }, wait=False)
    project_1.commit()
    db.session.commit()
    indexer.index(project_1)

    # project 2
    (project_2, video_1, video_2) = new_project(
        api_app, es, cds_jsonresolver, users,
        location, db, deposit_metadata,
        project_data={
            'title': {'title': 'alpha'},
            'description': 'fuu',
            'category': 'CERN',
            'type': 'FOOTER',
        }, wait=False)
    prepare_videos_for_publish([video_1, video_2])
    login_user(User.query.get(users[0]))
    project_2 = project_2.publish()
    project_2.commit()
    db.session.commit()
    indexer.index(project_2)
    # project 3
    (project_3, _, _) = new_project(
        api_app, es, cds_jsonresolver, users,
        location, db, deposit_metadata,
        project_data={
            'title': {'title': 'zeta'},
        }, wait=False)
    project_3['category'] = 'LHC'
    project_3.commit()
    db.session.commit()
    indexer.index(project_3)
    # project 4
    (project_4, _, _) = new_project(
        api_app, es, cds_jsonresolver, users,
        location, db, deposit_metadata,
        project_data={
            'title': {'title': 'project 2'},
        }, wait=False)
    project_4['category'] = 'ATLAS'
    project_4.commit()
    db.session.commit()
    indexer.index(project_4)
    sleep(2)

    def check_agg(agg, key, doc_count):
        [res] = list(filter(lambda x: x['key'] == key, agg['buckets']))
        assert res['doc_count'] == doc_count

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # test: get all
        res = client.get(
            url_for('invenio_deposit_rest.project_list'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        agg = data['aggregations']
        check_agg(agg['category'], 'CERN', 2)
        check_agg(agg['category'], 'LHC', 1)
        check_agg(agg['category'], 'ATLAS', 1)
        assert len(agg['category']['buckets']) == 3
        check_agg(agg['project_status'], 'draft', 3)
        check_agg(agg['project_status'], 'published', 1)
        assert len(agg['project_status']['buckets']) == 2

        # test: category == 'CERN'
        res = client.get(
            url_for('invenio_deposit_rest.project_list', category='CERN'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        agg = data['aggregations']
        check_agg(agg['category'], 'CERN', 2)
        assert len(agg['category']['buckets']) == 1
        check_agg(agg['project_status'], 'draft', 1)
        check_agg(agg['project_status'], 'published', 1)
        assert len(agg['project_status']['buckets']) == 2

        # test: project_status == 'draft'
        res = client.get(
            url_for('invenio_deposit_rest.project_list',
                    project_status='draft'),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        agg = data['aggregations']
        check_agg(agg['category'], 'CERN', 1)
        check_agg(agg['category'], 'LHC', 1)
        check_agg(agg['category'], 'ATLAS', 1)
        assert len(agg['category']['buckets']) == 3
        check_agg(agg['project_status'], 'draft', 3)
        assert len(agg['project_status']['buckets']) == 1


def test_sync_access_rights(
        api_app, api_project, es, cds_jsonresolver, users,
        location, db, deposit_metadata, json_headers, video_deposit_metadata,
        json_partial_video_headers, json_partial_project_headers):
    """Test default project order."""
    (project, video_1, video_2) = api_project
    video_1_depid = video_1['_deposit']['id']
    project_depid = project['_deposit']['id']
    # set access rights
    access_rights = {'update': ['my@email.it']}
    project['_access'] = deepcopy(access_rights)
    project.commit()
    prepare_videos_for_publish([video_1, video_2])
    project_dict = deepcopy(project.replace_refs())
    del project_dict['_files']
    db.session.commit()

    def check_record_access_rights(recid):
        # check video has same access rights of the project
        res = client.get(url_for('invenio_records_rest.recid_item',
                                 pid_value=recid))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert data['metadata']['_access'] == access_rights

    def check_video_access_rights(video_depid):
        # check video has same access rights of the project
        res = client.get(url_for('invenio_deposit_rest.video_item',
                                 pid_value=video_depid))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert data['metadata']['_access'] == access_rights

    def check_project_access_rights(project_depid):
        # check project didn't change access rights
        res = client.get(url_for('invenio_deposit_rest.project_item',
                                 pid_value=project_depid))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert data['metadata']['_access'] == access_rights

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # create a new video
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(_project_id=project['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        video_3_depid = data['metadata']['_deposit']['id']

        check_video_access_rights(video_3_depid)
        check_project_access_rights(project_depid)

        # try to update the project
        project_dict = deepcopy(project.replace_refs())
        del project_dict['_files']
        project_dict['title']['title'] = 'changed.. 1'
        res = client.put(
            url_for('invenio_deposit_rest.project_item',
                    pid_value=project_depid),
            data=json.dumps(project_dict),
            headers=json_partial_project_headers)
        assert res.status_code == 200

        check_video_access_rights(video_3_depid)
        check_project_access_rights(project_depid)

        # publish a video -> update project access rights
        res = client.post(url_for('invenio_deposit_rest.video_actions',
                                  pid_value=video_1_depid, action='publish'))
        assert res.status_code == 202
        data = json.loads(res.data.decode('utf-8'))
        recid = data['metadata']['recid']
        project_dict = deepcopy(project.replace_refs())
        del project_dict['_files']
        project_dict['title']['title'] = 'changed.. 2'
        # user1 can now access to the project
        access_rights['update'] = [User.query.get(users[1]).email]
        project_dict['_access'] = deepcopy(access_rights)
        res = client.put(
            url_for('invenio_deposit_rest.project_item',
                    pid_value=project_depid),
            data=json.dumps(project_dict),
            headers=json_partial_project_headers)
        assert res.status_code == 200

        check_record_access_rights(recid)
        check_project_access_rights(project_depid)

    with api_app.test_client() as client:
        user_2 = User.query.get(users[1])
        user_2_id = str(user_2.id)
        user_2_email = user_2.email

        @identity_loaded.connect
        def load_email(sender, identity):
            if current_user.get_id() == user_2_id:
                identity.provides.update([UserNeed(user_2_email)])

        # edit video as user1 (who has access to the video because previously
        # user0 give access to the project)
        login_user_via_session(client, email=user_2_email)
        res = client.post(url_for('invenio_deposit_rest.video_actions',
                                  pid_value=video_1_depid, action='edit'))
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))

        check_video_access_rights(video_3_depid)
        check_project_access_rights(project_depid)


def test_sync_owners(api_app, es, cds_jsonresolver, users,
                     location, db, deposit_metadata, json_headers,
                     json_partial_project_headers, video_deposit_metadata,
                     json_partial_video_headers):
    """Test default project order."""
    user_1 = User.query.get(users[0])
    user_1_id = str(user_1.id)
    user_1_email = user_1.email
    user_2 = User.query.get(users[1])
    user_2_id = str(user_2.id)
    user_2_email = user_2.email

    # user1 create a project
    (project, _, _) = new_project(
        api_app, es, cds_jsonresolver, users,
        location, db, deposit_metadata,
        project_data={
            'title': {'title': 'project 1'},
            'category': 'CERN',
        }, wait=False)
    assert project['_deposit']['owners'] == [users[0]]
    project_depid = project['_deposit']['id']

    # user1 give to user2 access to the project
    with api_app.test_client() as client:
        login_user_via_session(client, email=user_1_email)
        project_dict = deepcopy(project.replace_refs())
        del project_dict['_files']
        project_dict['_access'] = {'update': [user_2_email]}
        res = client.put(
            url_for('invenio_deposit_rest.project_item',
                    pid_value=project_depid),
            data=json.dumps(project_dict),
            headers=json_partial_project_headers)
        assert res.status_code == 200

    # user2 enter a new video
    with api_app.test_client() as client:
        @identity_loaded.connect
        def load_email(sender, identity):
            if current_user.get_id() == user_2_id:
                identity.provides.update([UserNeed(user_2_email)])
        login_user_via_session(client, email=user_2_email)
        video_metadata = deepcopy(video_deposit_metadata)
        video_metadata.update(_project_id=project['_deposit']['id'])
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps(video_metadata),
            headers=json_partial_video_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        video_depid = data['metadata']['_deposit']['id']
        # user 2 try to access to the new video
        res = client.get(url_for('invenio_deposit_rest.video_item',
                                 pid_value=video_depid))
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        # check user1 is the owner
        assert data['metadata']['_deposit']['created_by'] == int(user_1_id)

    # user1 try to access to the video entered by user2
    with api_app.test_client() as client:
        login_user_via_session(client, email=user_1_email)
        res = client.get(url_for('invenio_deposit_rest.video_item',
                                 pid_value=video_depid))
        assert res.status_code == 200


def test_project_edit_links(api_app, app, project_published, json_headers,
                            users):
    """Check project edit links."""
    (project, video_1, video_2) = project_published

    def check_links(url_video_1, result):
        res = client.get(url_video_1, headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert ('project_edit' in data['links']) is result
        if result:
            return data['links']['project_edit']

    #  check anonymous user can't see links
    with api_app.test_client() as client:
        url_video_1 = url_for('invenio_records_rest.recid_item',
                              pid_value=video_1['recid'])
        url_project = url_for('invenio_records_rest.recid_item',
                              pid_value=project['recid'])
        check_links(url_video_1, False)
        check_links(url_project, False)

    # check user2 can't see links
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        check_links(url_video_1, False)
        check_links(url_project, False)

    # check user1 (owner) can see links
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        project_link_1 = check_links(url_video_1, True)
        project_link_2 = check_links(url_project, True)
        assert project_link_1 == project_link_2
    # check project links
    with app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        res = client.get(project_link_1, headers=json_headers)
        assert res.status_code == 200


def test_modified_by(api_app, api_project, users, json_headers):
    """Test modified_by on publish."""
    (project, video_1, video_2) = api_project
    v1_depid = video_1['_deposit']['id']
    v2_depid = video_2['_deposit']['id']
    p_depid = project['_deposit']['id']
    prepare_videos_for_publish([video_1, video_2])

    # check modified_by
    assert 'modified_by' not in video_1['_cds']
    assert 'modified_by' not in video_2['_cds']
    assert 'modified_by' not in project['_cds']

    user_1 = User.query.get(users[0])
    with api_app.test_client() as client:
        # login as user_1
        login_user_via_session(client, email=user_1.email)
        # publish video_1
        res = client.post(
            url_for('invenio_deposit_rest.video_actions',
                    pid_value=v1_depid, action='publish'),
            headers=json_headers)
        assert res.status_code == 202
        # check
        [video_1, video_2] = deposit_videos_resolver([v1_depid, v2_depid])
        project = deposit_project_resolver(p_depid)
        assert video_1['_cds']['modified_by'] == user_1.id
        assert 'modified_by' not in video_2['_cds']
        assert 'modified_by' not in project['_cds']

        # publish project
        res = client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=p_depid, action='publish'),
            headers=json_headers)
        assert res.status_code == 202
        # check
        [video_1, video_2] = deposit_videos_resolver([v1_depid, v2_depid])
        project = deposit_project_resolver(p_depid)
        assert video_1['_cds']['modified_by'] == user_1.id
        assert video_2['_cds']['modified_by'] == user_1.id
        assert project['_cds']['modified_by'] == user_1.id
