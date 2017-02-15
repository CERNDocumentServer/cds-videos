# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017 CERN.
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

"""Test video."""

from __future__ import absolute_import, print_function

import mock
import pytest
import json

from time import sleep
from celery import states
from invenio_db import db
from flask import url_for
from invenio_webhooks import current_webhooks
from invenio_webhooks.models import Event
from mock import MagicMock
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_records.models import RecordMetadata
from six import BytesIO
from invenio_indexer.api import RecordIndexer
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from copy import deepcopy
from jsonschema.exceptions import ValidationError

from cds.modules.deposit.api import (record_build_url, video_build_url,
                                     video_resolver, Video)
from cds.modules.webhooks.status import get_deposit_events, \
    get_tasks_status_by_task

from helpers import workflow_receiver_video_failing, mock_current_user, \
    get_indexed_records_from_mock, prepare_videos_for_publish


def test_video_resolver(project):
    """Test vide resolver."""
    (project, video_1, video_2) = project
    videos = video_resolver(
        [video_1['_deposit']['id'], video_2['_deposit']['id']])
    original = [video_1.id, video_2.id]
    original.sort()
    resolved = [videos[0].id, videos[1].id]
    resolved.sort()
    assert original == resolved


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_video_publish_and_edit(project):
    """Test video publish and edit."""
    (project, video_1, video_2) = project
    video_path_1 = project['videos'][0]['$reference']
    video_path_2 = project['videos'][1]['$reference']

    deposit_project_schema = ('https://cdslabs.cern.ch/schemas/'
                              'deposits/records/project-v1.0.0.json')
    deposit_video_schema = ('https://cdslabs.cern.ch/schemas/'
                            'deposits/records/video-v1.0.0.json')
    record_video_schema = ('https://cdslabs.cern.ch/schemas/'
                           'records/video-v1.0.0.json')

    # check video1 is not published
    assert video_1['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # and the schema is a deposit
    assert video_1['$schema'] == deposit_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema

    # update video

    # [publish the video 1]
    prepare_videos_for_publish(video_1)
    video_1 = video_1.publish()

    project = video_1.project
    (_, record_video_1) = video_1.fetch_published()
    record_video_id_1 = record_video_1['recid']
    record_path_1 = record_build_url(record_video_id_1)

    # check new link project -> video
    assert video_1['_deposit']['status'] == 'published'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # check the schema is a record
    assert record_video_1['$schema'] == record_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema
    # check video recid is inside the list
    assert any(video_ref['$reference'] == record_path_1
               for video_ref in project['videos']) is True
    # and there is not the old id (when the video was a deposit)
    assert any(video_ref['$reference'] == video_path_1
               for video_ref in project['videos']) is False
    # and still exists video 2 deposit id
    assert any(video_ref['$reference'] == video_path_2
               for video_ref in project['videos']) is True

    # [edit the video 1]
    [video_1_v2] = video_resolver([record_video_1['_deposit']['id']])
    video_1_v2 = video_1_v2.edit()

    # check video1 is not published
    assert video_1_v2['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # check the schema is a record
    assert video_1_v2['$schema'] == deposit_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema
    # check video1 v1 recid is NOT inside the list
    assert any(video_ref['$reference'] == record_path_1
               for video_ref in project['videos']) is False
    # check video1 v2 is inside the list
    video_path_1_v2 = video_build_url(video_1_v2['_deposit']['id'])
    assert any(video_ref['$reference'] == video_path_1_v2
               for video_ref in project['videos']) is True


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False, True])
def test_delete_video_not_published(project, force):
    """Test video delete when draft."""
    (project, video_1, video_2) = project

    project_id = project.id
    video_1_ref = video_1.ref
    video_2_id = video_2.id

    assert project.status == 'draft'
    assert video_2.status == 'draft'

    video_2.delete(force=force)

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert [{'$reference': video_1_ref}] == project_meta.json['videos']

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    if force:
        assert video_2_meta is None
    else:
        assert video_2_meta.json is None


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False, True])
def test_delete_video_published(project, force):
    """Test video delete after published."""
    (project, video_1, video_2) = project
    prepare_videos_for_publish(video_1, video_2)

    video_2 = video_2.publish()

    project_id = project.id
    video_2_id = video_2.id
    video_2_ref = video_2.ref

    assert project.status == 'draft'
    assert video_2.status == 'published'

    with pytest.raises(PIDInvalidAction):
        video_2.delete(force=force)

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    assert video_2_meta.json is not None

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert {'$reference': video_2_ref} in project_meta.json['videos']


def test_video_dumps(db, project, video):
    """Test video dump, in particular file dump."""
    (project, video_1, video_2) = project
    bucket_id = video_1['_buckets']['deposit']
    obj = ObjectVersion.create(
        bucket=bucket_id, key='master.mp4', stream=open(video, 'rb'))
    slave_1 = ObjectVersion.create(
        bucket=bucket_id, key='slave_1.mp4', stream=open(video, 'rb'))
    ObjectVersionTag.create(slave_1, 'master', str(obj.version_id))
    ObjectVersionTag.create(slave_1, 'media_type', 'video')
    ObjectVersionTag.create(slave_1, 'context_type', 'subformat')

    for i in reversed(range(10)):
        slave = ObjectVersion.create(
            bucket=bucket_id, key='frame-{0}.jpeg'.format(i),
            stream=BytesIO(b'\x00' * 1024))
        ObjectVersionTag.create(slave, 'master', str(obj.version_id))
        ObjectVersionTag.create(slave, 'media_type', 'image')
        ObjectVersionTag.create(slave, 'context_type', 'frame')

    db.session.commit()

    files = video_1.files.dumps()

    assert len(files) == 1
    files = files[0]  # only one master file

    assert 'frame' in files
    assert [f['key'] for f in files['frame']] == [
        'frame-{}.jpeg'.format(i) for i in range(10)]
    assert 'subformat' in files
    assert len(files['subformat']) == 1


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_video_delete_with_workflow(app, users, project, webhooks, es):
    """Test publish a project with a workflow."""
    project, video_1, video_2 = project
    video_1_depid = video_1['_deposit']['id']

    receiver_id = 'test_video_delete_with_workflow'
    workflow_receiver_video_failing(
        app, db, video_1, receiver_id=receiver_id)

    mock_delete = MagicMock(return_value=None)
    current_webhooks.receivers[receiver_id].delete = mock_delete

    headers = [('Content-Type', 'application/json')]
    payload = json.dumps(dict(somekey='somevalue'))
    with app.test_request_context(headers=headers, data=payload):
        event = Event.create(receiver_id=receiver_id)
        db.session.add(event)
        event.process()
    db.session.commit()

    video_1 = video_resolver([video_1_depid])[0]
    video_1.delete()
    assert mock_delete.called is True


def test_video_record_schema(app, db, project):
    """Test video record schema."""
    (project, video_1, video_2) = project
    assert video_1.record_schema == Video.get_record_schema()


@mock.patch('flask_login.current_user', mock_current_user)
def test_video_events_on_download_check_index(api_app, webhooks, db,
                                              api_project, access_token,
                                              json_headers, users):
    """Test deposit events."""
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish(video_1, video_2)
    project_depid = project['_deposit']['id']
    video_1_depid = video_1['_deposit']['id']
    bucket_id = video_1._bucket.id

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        file_size = 1024 * 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            bucket_id=str(bucket_id),
            deposit_id=video_1_depid,
            key='test.pdf')

        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 201

        # run indexer
        RecordIndexer().process_bulk_queue()
        sleep(2)

        deposit = video_resolver([video_1_depid])[0]
        file_dumps = deposit._get_files_dump()
        assert len(file_dumps) == 1

        def search_record(url):
            res = client.get(url, headers=json_headers)
            assert res.status_code == 200
            data = json.loads(
                res.data.decode('utf-8')
            )['hits']['hits'][0]['metadata']
            return data

        # check if the tasks states and files are inside elasticsearch
        # -> check video
        url_video_deposit = url_for('invenio_deposit_rest.video_list',
                                    q='_deposit.id:{0}'.format(video_1_depid),
                                    access_token=access_token)
        data = search_record(url_video_deposit)
        assert data['_deposit']['state']['file_download'] == states.SUCCESS
        assert file_dumps == data['_files']
        # -> check project
        url_project_deposit = url_for(
            'invenio_deposit_rest.project_list',
            q='_deposit.id:{0}'.format(project_depid),
            access_token=access_token)
        search_record(url_project_deposit)
        assert data['_deposit']['state']['file_download'] == states.SUCCESS

        # [[ EDIT VIDEO ]]
        video_edited = deepcopy(deposit)
        del video_edited['_files']
        del video_edited['_deposit']['state']
        client.put(
            url_for('invenio_deposit_rest.video_item',
                    pid_value=video_1_depid),
            data=json.dumps(video_edited),
            headers=json_headers)

        # check if the tasks states and files are inside elasticsearch
        # -> check video
        data = search_record(url_video_deposit)
        assert data['_deposit']['state']['file_download'] == states.SUCCESS
        assert file_dumps == data['_files']
        # -> check project
        url_project_deposit = url_for(
            'invenio_deposit_rest.project_list',
            q='_deposit.id:{0}'.format(project_depid),
            access_token=access_token)
        search_record(url_project_deposit)
        assert data['_deposit']['state']['file_download'] == states.SUCCESS

        # [[ PUBLISH THE PROJECT ]]
        res = client.post(
            url_for('invenio_deposit_rest.project_actions',
                    pid_value=project['_deposit']['id'], action='publish',
                    ), headers=json_headers)
        assert res.status_code == 202

        # run indexer
        RecordIndexer().process_bulk_queue()
        sleep(2)

        deposit = video_resolver([video_1_depid])[0]

        # check if the files are inside elasticsearch
        # -> check video deposit
        data = search_record(url_video_deposit)
        assert data['_deposit']['state']['file_download'] == states.SUCCESS
        assert file_dumps == data['_files']
        # check video record
        pid, record = deposit.fetch_published()
        url = url_for('invenio_records_rest.recid_list',
                      q='_deposit.pid.value:{0}'.format(pid.pid_value))
        data = search_record(url)
        assert record['_files'] == data['_files']


@mock.patch('flask_login.current_user', mock_current_user)
def test_video_events_on_download(api_app, webhooks, db, api_project,
                                  access_token, json_headers):
    """Test deposit events."""
    (project, video_1, video_2) = api_project
    video_1_depid = video_1['_deposit']['id']
    project_id = str(project.id)
    video_1_id = str(video_1.id)
    bucket_id = video_1._bucket.id

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_indexer, \
            api_app.test_client() as client:
        file_size = 1024 * 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            bucket_id=str(bucket_id),
            deposit_id=video_1_depid,
            key='test.pdf')

        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 201

        file_size = 1024 * 1024 * 6
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 201

        deposit = video_resolver([video_1_depid])[0]

        events = get_deposit_events(deposit['_deposit']['id'])

        assert len(events) == 2
        assert events[0].payload['deposit_id'] == video_1_depid
        assert events[1].payload['deposit_id'] == video_1_depid

        status = get_tasks_status_by_task(events)
        assert status == {'file_download': states.SUCCESS}

        # check if the states are inside the deposit
        res = client.get(
            url_for('invenio_deposit_rest.video_item', pid_value=video_1_depid,
                    access_token=access_token),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))['metadata']
        assert data['_deposit']['state']['file_download'] == states.SUCCESS
        assert deposit._get_files_dump() == data['_files']

        # check the record is inside the indexer queue
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert len(ids) == 2
        assert video_1_id in ids
        assert project_id in ids


@mock.patch('flask_login.current_user', mock_current_user)
def test_video_events_on_workflow(webhooks, api_app, db, api_project, bucket,
                                  access_token, json_headers):
    """Test deposit events."""
    (project, video_1, video_2) = api_project
    project_depid = project['_deposit']['id']
    video_1_depid = video_1['_deposit']['id']
    db.session.add(bucket)

    # registering receiver
    sse_channel = 'mychannel'
    receiver_id = 'test_video_events_on_workflow'
    workflow_receiver_video_failing(
        api_app, db, video_1, receiver_id=receiver_id, sse_channel=sse_channel)

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
        deposit = video_resolver([video_1_depid])[0]
        events = get_deposit_events(deposit['_deposit']['id'])
        # check events
        assert len(events) == 2
        assert events[0].payload['deposit_id'] == video_1_depid
        assert events[1].payload['deposit_id'] == video_1_depid
        # check computed status
        status = get_tasks_status_by_task(events)
        assert status['add'] == states.SUCCESS
        assert status['failing'] == states.FAILURE

        # check every task for every event
        for event in events:
            result = event.receiver._deserialize_result(event)
            assert result.parent.status == states.SUCCESS
            assert result.children[0].status == states.FAILURE
            assert result.children[1].status == states.SUCCESS

        # check if the states are inside the deposit
        res = client.get(
            url_for('invenio_deposit_rest.video_item', pid_value=video_1_depid,
                    access_token=access_token),
            headers=json_headers)
        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))['metadata']
        assert data['_deposit']['state']['add'] == states.SUCCESS
        assert data['_deposit']['state']['failing'] == states.FAILURE

        # run indexer
        RecordIndexer().process_bulk_queue()
        sleep(2)
        # check elasticsearch video_1 state
        resp = client.get(url_for('invenio_deposit_rest.video_list',
                                  q='_deposit.id:{0}'.format(video_1_depid),
                                  access_token=access_token),
                          headers=json_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data.decode('utf-8'))
        status = data['hits']['hits'][0]['metadata']['_deposit']['state']
        assert status['add'] == states.SUCCESS
        assert status['failing'] == states.FAILURE
        # check elasticsearch project state
        resp = client.get(url_for('invenio_deposit_rest.video_list',
                                  q='_deposit.id:{0}'.format(project_depid),
                                  access_token=access_token),
                          headers=json_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data.decode('utf-8'))
        status = data['hits']['hits'][0]['metadata']['_deposit']['state']
        assert status['add'] == states.SUCCESS
        assert status['failing'] == states.FAILURE


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_video_publish_with_no_category(project):
    """Test video publish if category is not set."""
    (project, video_1, video_2) = project
    prepare_videos_for_publish(video_1, video_2)
    video_1_depid = video_1['_deposit']['id']
    # test: no category in project
    category = project['category']
    del project['category']
    assert 'type' in project
    project.commit()
    db.session.commit()
    with pytest.raises(ValidationError):
        video_1.publish()
    # test: no type in project
    type_ = project['type']
    project['category'] = category
    del project['type']
    assert 'category' in project
    project.commit()
    db.session.commit()
    video_1 = video_resolver([video_1_depid])[0]
    with pytest.raises(ValidationError):
        video_1.publish()
    # test with category + type
    project['type'] = type_
    project.commit()
    db.session.commit()
    video_1 = video_resolver([video_1_depid])[0]
    video_1.publish()
    assert video_1['_deposit']['status'] == 'published'
