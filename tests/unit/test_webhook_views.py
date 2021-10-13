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

"""CDS tests for Webhook views."""

from __future__ import absolute_import, print_function

import json
import pytest

import mock
from celery.result import AsyncResult
from celery import states
from flask import url_for
from flask_security import current_user
from flask_principal import UserNeed, identity_loaded
from helpers import get_object_count, get_tag_count, mock_current_user, \
    workflow_receiver_video_failing
from invenio_files_rest.models import ObjectVersion, \
    ObjectVersionTag, Bucket
from invenio_records.models import RecordMetadata
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.webhooks.status import get_deposit_flows
from cds.modules.flows.models import Flow as FlowModel

from helpers import get_indexed_records_from_mock, get_local_file


def check_restart_avc_workflow(api_app, event_id, access_token,
                               json_headers, data, video_1_id, video_1_depid,
                               users):
    """Try to restart AVC workflow via REST API."""
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_item',
            receiver_id='avc',
            event_id=event_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay')as mock_indexer:
        resp = client.put(url, headers=json_headers)

        assert resp.status_code == 201

    # (Create + Clean + Create) * Objects Count
    assert ObjectVersion.query.count() == 3 * get_object_count()
    # (Version 1 + Version 2) * Tags Count
    assert ObjectVersionTag.query.count() == 2 * get_tag_count()

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']

    # check elasticsearch
    assert mock_indexer.called is True
    ids = get_indexed_records_from_mock(mock_indexer)
    setids = set(ids)
    assert len(setids) == 2
    assert video_1_id in setids

    # check restart from anonymous user
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_item',
            receiver_id='avc',
            event_id=event_id,
        )
    with api_app.test_client() as client:
        resp = client.put(url, headers=json_headers)
        assert resp.status_code == 401

    # check feedback from another user without access
    user_2 = User.query.get(users[1])
    user_2_email = user_2.email
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_item',
            receiver_id='avc',
            event_id=event_id,
        )
    with api_app.test_client() as client:
        login_user_via_session(client, email=user_2_email)
        resp = client.put(url, headers=json_headers)
        assert resp.status_code == 403

    # check feedback from another user with access
    user_2 = User.query.get(users[1])
    user_2_id = str(user_2.id)
    user_2_email = user_2.email
    project = deposit_video_resolver(video_1_depid).project
    project['_access'] = {'update': [user_2_email]}
    project.commit()
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_item',
            receiver_id='avc',
            event_id=event_id,
        )
    with api_app.test_client() as client:

        @identity_loaded.connect
        def load_email(sender, identity):
            if current_user.get_id() == user_2_id:
                identity.provides.update([UserNeed(user_2_email)])

        login_user_via_session(client, email=user_2_email)
        resp = client.put(url, headers=json_headers)
        assert resp.status_code == 201


def check_video_transcode_delete(api_app, event_id, access_token,
                                 json_headers, data, video_1_id, video_1_depid,
                                 users):
    """Try to delete transcoded file via REST API."""
    # get the list of task id of successfully transcode tasks
    task_ids = [d['file_transcode']['id']
                for d in data['global_status'][1]
                if 'file_transcode' in d and
                d['file_transcode']['status'] == 'SUCCESS']
    # DELETE FIRST TRANSCODED FILE
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_ids[0],
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 204

    # Create + Delete first transcode
    assert ObjectVersion.query.count() == (
        get_object_count() + 1
    )
    # Also if the tags are deleted, they remain associated with last version
    # of transcoded file
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']

    # check bucket size
    bucket = Bucket.query.first()
    assert bucket.size == 0

    # DELETE SECOND TRANSCODED FILE
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_ids[1],
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 204

    # Create + 2 Deleted transcode files
    assert ObjectVersion.query.count() == get_object_count() + 2
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']


def check_video_transcode_restart(api_app, event_id, access_token,
                                  json_headers, data, video_1_id,
                                  video_1_depid, users):
    """Try to delete transcoded file via REST API."""
    task_ids = [d['id']
                for d in data['_tasks'][1]
                if d['name'] == 'file_transcode' and
                d['status'] == 'SUCCESS']
    # RESTART FIRST TRANSCODED FILE
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_ids[0],
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.put(url, headers=json_headers)

        assert resp.status_code == 204

    # Create + restart transcode (clean + create)
    assert ObjectVersion.query.count() == get_object_count() + 2
    # if changed, copy magic number 14 from helpers::get_tag_count
    assert ObjectVersionTag.query.count() == get_tag_count() + 14

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']

    # check task id is changed
    flow = FlowModel.query.first()
    new_task_id = flow.response['global_status'][1][1]['file_transcode']['id']
    assert task_ids[0] != new_task_id
    old_result = AsyncResult(task_ids[0])
    new_result = AsyncResult(new_task_id)
    for key in ['tags', 'key', 'deposit_id', 'flow_id', 'preset_quality']:
        assert old_result.result[
            'payload'][key] == new_result.result['payload'][key]


def check_video_frames(api_app, event_id, access_token,
                       json_headers, data, video_1_id, video_1_depid, users):
    """Try to delete video frames via REST API."""
    task_id = data['_tasks'][1][0]['id']
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == (
        get_object_count() +
        get_object_count(download=False, transcode=False)
    )
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']


def check_video_download(api_app, event_id, access_token,
                         json_headers, data, video_1_id, video_1_depid, users):
    """Try to delete downloaded files via REST API."""
    task_id = data['_tasks'][0][0]['id']
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 204

    # Create + Delete Download
    assert ObjectVersion.query.count() == (
        get_object_count() + get_object_count(frames=False, transcode=False)
    )
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is not there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']


def check_video_metadata_extraction(api_app, event_id, access_token,
                                    json_headers, data, video_1_id,
                                    video_1_depid, users):
    """Try to delete metadata extraction via REST API."""
    task_id = data['_tasks'][0][1]['id']
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is not there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' not in record.json['_cds']


@pytest.mark.skip(reason='Functionality not used')
@pytest.mark.parametrize('checker', [
    check_restart_avc_workflow,
    check_video_metadata_extraction,
    check_video_download,
    check_video_frames,
    check_video_transcode_delete,
    check_video_transcode_restart,
])
@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_delete(api_app, db, api_project, users,
                             access_token, json_headers, mock_sorenson,
                             online_video, webhooks, checker):
    """Test AVCWorkflow receiver REST API."""
    project, video_1, video_2 = api_project
    video_1_id = video_1.id
    video_1_depid = video_1['_deposit']['id']
    master_key = 'test.mp4'

    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        payload = dict(
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

    # check extracted metadata is there
    record = RecordMetadata.query.get(video_1_id)
    assert 'extracted_metadata' in record.json['_cds']

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    event_id = data['tags']['_event_id']
    video_1_id = str(deposit_video_resolver(video_1_depid).id)
    ###
    checker(api_app, event_id, access_token, json_headers, data,
            video_1_id, video_1_depid, users)


def test_webhooks_failing_feedback(api_app, db, cds_depid, access_token,
                                   json_headers, api_project, local_file):
    """Test webhooks feedback with a failing task."""
    (project, video_1, video_2) = api_project
    receiver_id = 'test_feedback_with_workflow'
    video_depid = video_1['_deposit']['id']
    bucket_id = str(video_1.files.bucket.id)
    version_id = str(local_file)
    key = 'TEST.mp4'
    workflow_receiver_video_failing(api_app, db, video_1,
                                    receiver_id, version_id,
                                    )

    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_list',
            receiver_id=receiver_id,
            access_token=access_token
        )

    with api_app.test_client() as client:
        # run workflow
        resp = client.post(url, headers=json_headers,
                           data=json.dumps(
                               dict(deposit_id=video_depid,
                                    bucket_id=bucket_id,
                                    version_id=version_id,
                                    key=key)
                           ))
        assert resp.status_code == 500
        #  data = json.loads(resp.data.decode('utf-8'))

        # check feedback url
        flow_id = resp.headers['X-Hub-Delivery']
        #  event_id = data['tags']['_event_id']
        with api_app.test_request_context():
            url = url_for('cds_webhooks.flow_feedback_item',
                          flow_id=flow_id, access_token=access_token,
                          receiver_id=receiver_id)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data.decode('utf-8'))
        assert data[0][0] == {'add': 3}
        assert data[1][0] == {'failing': ''}


@pytest.mark.skip(reason='Functionality not used')
@pytest.mark.parametrize('receiver_id', ['avc', 'downloader'])
def test_webhooks_delete(api_app, access_token, json_headers,
                         online_video, api_project, users, receiver_id,
                         local_file, mock_sorenson):
    """Test webhooks delete."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    master_key = 'test.mp4'

    # run workflow!
    with api_app.test_request_context():
        url = url_for(
            'cds_webhooks.flow_list',
            receiver_id=receiver_id,
            access_token=access_token
        )

    # check no events are there
    assert get_deposit_flows(video_1_depid) == []

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):
        payload = dict(
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
        )

        if receiver_id != 'downloader':
            payload['version_id'] = str(local_file)

        # run the workflow!
        login_user_via_session(client, email=User.query.get(users[0]).email)
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        # check event is created
        assert resp.status_code == 201
        flow_id = resp.headers['X-Hub-Delivery']
        [flow] = get_deposit_flows(video_1_depid)
        assert str(flow.id) == flow_id

        # delete event
        url_to_delete = url_for(
            'cds_webhooks.flow_item',
            receiver_id=receiver_id,
            event_id=str(flow_id),
            access_token=access_token
        )
        res = client.delete(url_to_delete, headers=json_headers)
        assert res.status_code == 201
        # check no events are there
        assert get_deposit_flows(video_1_depid) == []
        # check event is marked as deleted
        [flow_deleted] = FlowModel.query.all()
        assert flow_deleted.id == flow.id
        assert flow_deleted.response_code == 410


def test_webhooks_reload_master(api_app, users, access_token, json_headers,
                                online_video, api_project, datadir,
                                mock_sorenson):
    """Test webhooks reload master after publish/edit/publish."""
    api_app.config['DEPOSIT_DATACITE_MINTING_ENABLED'] = False

    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    master_key = 'test.mp4'
    receiver_id = 'avc'

    with api_app.test_request_context():
        url_run_workflow = url_for(
            'cds_webhooks.flow_list',
            receiver_id=receiver_id,
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay'):

        # create local file
        local_file = get_local_file(bucket=video_1.files.bucket,
                                    datadir=datadir, filename='test.mp4')

        payload = dict(
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
            version_id=str(local_file),
            bucket_id=str(video_1.files.bucket.id)
        )

        # run the workflow!
        login_user_via_session(client, email=User.query.get(users[0]).email)
        resp = client.post(url_run_workflow, headers=json_headers,
                           data=json.dumps(payload))
        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))
        flow_id = data['tags']['_flow_id']

        # publish video
        publish_url = url_for('invenio_deposit_rest.video_actions',
                              pid_value=video_1_depid, action='publish')
        resp = client.post(publish_url, headers=json_headers)
        assert resp.status_code == 202

        # edit video
        edit_url = url_for('invenio_deposit_rest.video_actions',
                           pid_value=video_1_depid, action='edit')
        resp = client.post(edit_url, headers=json_headers)
        assert resp.status_code == 201

        video_1 = deposit_video_resolver(video_1_depid)

        # delete old worflow
        url_delete = url_for('cds_webhooks.flow_item',
                             receiver_id=receiver_id,
                             flow_id=str(flow_id),
                             access_token=access_token)
        resp = client.delete(url_delete, headers=json_headers)

        # run the workflow!
        resp = client.post(url_run_workflow, headers=json_headers,
                           data=json.dumps(payload))
        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))
        flow_id = data['tags']['_flow_id']

        # publish again
        resp = client.post(publish_url, headers=json_headers)
        assert resp.status_code == 202
