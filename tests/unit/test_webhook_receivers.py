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

"""CDS tests for Webhook receivers."""

from __future__ import absolute_import, print_function

import json

import mock
from cds_sorenson.api import get_all_distinct_qualities
from flask import url_for
from flask_principal import UserNeed, identity_loaded
from flask_security import current_user

from invenio_files_rest.models import ObjectVersion, \
    Bucket, ObjectVersionTag
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
import pytest
from invenio_records.models import RecordMetadata
from invenio_accounts.testutils import login_user_via_session
from invenio_accounts.models import User
from cds.modules.deposit.api import deposit_project_resolver

from celery import states, chain, group
from celery.result import AsyncResult
from invenio_webhooks import current_webhooks
from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.webhooks.status import collect_info, \
    get_tasks_status_by_task, get_deposit_events, iterate_events_results
from cds.modules.webhooks.receivers import CeleryAsyncReceiver
from cds.modules.webhooks.status import CollectInfoTasks
from invenio_webhooks.models import Event
from six import BytesIO

from helpers import failing_task, get_object_count, get_tag_count, \
    simple_add, mock_current_user, success_task, \
    get_indexed_records_from_mock, get_presets_applied


@mock.patch('flask_login.current_user', mock_current_user)
def test_download_receiver(api_app, db, api_project, access_token, webhooks,
                           json_headers):
    """Test downloader receiver."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    video_1_id = str(video_1.id)
    project_id = str(project.id)

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:

        file_size = 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            deposit_id=video_1_depid,
            key='test.pdf'
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == 'http://example.com/test.pdf'
        assert data['key'] == 'test.pdf'
        assert 'version_id' in data
        assert 'links' in data  # TODO decide with links are needed
        assert all([link in data['links']
                    for link in ['self', 'version', 'cancel']])

        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        tags = obj.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert obj.key == data['key']
        assert str(obj.version_id) == data['version_id']
        assert obj.file
        assert obj.file.size == file_size

        def set_data(state, message, size, total, percentage, type_):
            return {
                'state': state,
                'meta': {
                    'message': message,
                    'payload': {
                        'event_id': str(tags['_event_id']),
                        'key': u'test.pdf',
                        'tags': {
                            u'uri_origin': u'http://example.com/test.pdf',
                            u'_event_id': str(tags['_event_id']),
                            u'context_type': u'master',
                        },
                        'deposit_id': video_1_depid,
                        'percentage': percentage,
                        'version_id': str(obj.version_id),
                        'size': size,
                        'total': total,
                        'type': type_
                    }
                }
            }
        deposit = deposit_video_resolver(video_1_depid)

        # check ElasticSearch is called
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert video_1_id in ids
        assert project_id in ids
        assert deposit['_cds']['state'] == {
            u'file_download': states.SUCCESS}

    # Test cleaning!
    url = '{0}?access_token={1}'.format(data['links']['cancel'], access_token)

    with mock.patch('requests.get'), \
            mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 201

        assert ObjectVersion.query.count() == 2
        bucket = Bucket.query.first()
        assert bucket.size == 0

        assert mock_indexer.called is False


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_pass(api_app, db, api_project, access_token,
                                    json_headers, mock_sorenson, online_video,
                                    webhooks, users):
    """Test AVCWorkflow receiver."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    video_1_id = str(video_1.id)
    project_id = str(project.id)

    bucket_id = video_1['_buckets']['deposit']
    video_size = 5510872
    master_key = 'test.mp4'
    slave_keys = ['{0}.mp4'.format(quality)
                  for quality in get_presets_applied()
                  if quality != '1024p']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay') \
            as mock_indexer:
        payload = dict(
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == online_video
        assert data['key'] == master_key
        assert 'version_id' in data
        assert data.get('presets') == get_all_distinct_qualities()
        assert 'links' in data  # TODO decide with links are needed

        assert ObjectVersion.query.count() == get_object_count()

        # Master file
        master = ObjectVersion.get(bucket_id, master_key)
        tags = master.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert master.key == master_key
        assert str(master.version_id) == data['version_id']
        assert master.file
        assert master.file.size == video_size

        # Check metadata tags
        metadata_keys = ['duration', 'bit_rate', 'size', 'avg_frame_rate',
                         'codec_name', 'codec_long_name', 'width', 'height',
                         'nb_frames', 'display_aspect_ratio', 'color_range']
        assert all([key in tags for key in metadata_keys])

        # Check metadata patch
        recid = PersistentIdentifier.get('depid', video_1_depid).object_uuid
        record = Record.get_record(recid)
        assert 'extracted_metadata' in record['_cds']
        assert all([key in str(record['_cds']['extracted_metadata'])
                    for key in metadata_keys])

        # Check slaves
        for slave_key in slave_keys:
            slave = ObjectVersion.get(bucket_id, slave_key)
            tags = slave.get_tags()
            assert slave.key == slave_key
            assert '_sorenson_job_id' in tags
            assert tags['_sorenson_job_id'] == '1234'
            assert 'master' in tags
            assert tags['master'] == str(master.version_id)
            assert master.file
            assert master.file.size == video_size

        video = deposit_video_resolver(video_1_depid)
        events = get_deposit_events(video['_deposit']['id'])

        # check deposit tasks status
        tasks_status = get_tasks_status_by_task(events)
        assert len(tasks_status) == 4
        assert 'file_download' in tasks_status
        assert 'file_transcode' in tasks_status
        assert 'file_video_extract_frames' in tasks_status
        assert 'file_video_metadata_extraction' in tasks_status

        # check single status
        collector = CollectInfoTasks()
        iterate_events_results(events=events, fun=collector)
        info = list(collector)
        presets = get_presets_applied().keys()
        assert info[0][0] == 'file_download'
        assert info[0][1].status == states.SUCCESS
        assert info[1][0] == 'file_video_metadata_extraction'
        assert info[1][1].status == states.SUCCESS
        assert info[2][0] == 'file_video_extract_frames'
        assert info[2][1].status == states.SUCCESS
        for i in info[3:]:
            assert i[0] == 'file_transcode'
            if i[1].status == states.SUCCESS:
                assert i[1].result['payload']['preset_quality'] in presets

        # check tags
        assert ObjectVersionTag.query.count() == get_tag_count()

        deposit = deposit_video_resolver(video_1_depid)

        # check ElasticSearch is called
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert video_1_id in ids
        assert project_id in ids
        assert deposit['_cds']['state'] == {
            'file_download': states.SUCCESS,
            'file_video_metadata_extraction': states.SUCCESS,
            'file_video_extract_frames': states.SUCCESS,
            'file_transcode': states.SUCCESS,
        }

    # check feedback from anoymous user
    event_id = data['tags']['_event_id']
    with api_app.test_request_context():
        url = url_for('invenio_webhooks.event_feedback_item',
                      event_id=event_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 401
    # check feedback from owner
    with api_app.test_request_context():
        url = url_for('invenio_webhooks.event_feedback_item',
                      event_id=event_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 200
    # check feedback from another user without access
    with api_app.test_request_context():
        url = url_for('invenio_webhooks.event_feedback_item',
                      event_id=event_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 403
    # check feedback from another user with access
    user_2 = User.query.get(users[1])
    user_2_id = str(user_2.id)
    user_2_email = user_2.email
    project = deposit_project_resolver(project['_deposit']['id'])
    project['_access'] = {'update': [user_2_email]}
    project = project.commit()
    with api_app.test_request_context():
        url = url_for('invenio_webhooks.event_feedback_item',
                      event_id=event_id,
                      receiver_id='avc')
    with api_app.test_client() as client:

        @identity_loaded.connect
        def load_email(sender, identity):
            if current_user.get_id() == user_2_id:
                identity.provides.update([UserNeed(user_2_email)])

        login_user_via_session(client, email=user_2_email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 200

    # Test cleaning!
    url = '{0}?access_token={1}'.format(data['links']['cancel'], access_token)

    with mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 201

        # check that object versions and tags are deleted
        # (Create + Delete) * Num Objs
        assert ObjectVersion.query.count() == 2 * get_object_count()
        # Tags connected with the old version
        assert ObjectVersionTag.query.count() == get_tag_count()
        bucket = Bucket.query.first()
        # and bucket is empty
        assert bucket.size == 0

        record = RecordMetadata.query.filter_by(id=video_1_id).one()

        # check metadata patch are deleted
        assert 'extracted_metadata' not in record.json['_cds']

        # check the corresponding Event persisted after cleaning
        assert len(get_deposit_events(record.json['_deposit']['id'])) == 0
        assert len(get_deposit_events(record.json['_deposit']['id'],
                                      _deleted=True)) == 1

        # check no reindexing is fired
        assert mock_indexer.called is False


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_local_file_pass(
        api_app, db, api_project, access_token, json_headers,
        mock_sorenson, online_video, webhooks, local_file):
    """Test AVCWorkflow receiver."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    video_1_id = str(video_1.id)
    project_id = str(project.id)

    bucket_id = ObjectVersion.query.filter_by(
        version_id=local_file).one().bucket_id
    video_size = 5510872
    master_key = 'test.mp4'
    slave_keys = ['{0}.mp4'.format(quality)
                  for quality in get_presets_applied().keys()
                  if quality != '1024p']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay') \
            as mock_indexer:
        payload = dict(
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
            version_id=str(local_file),
        )
        # [[ RUN WORKFLOW ]]
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['key'] == master_key
        assert 'version_id' in data
        assert data.get('presets') == get_all_distinct_qualities()
        assert 'links' in data  # TODO decide with links are needed

        assert ObjectVersion.query.count() == get_object_count()

        # Master file
        master = ObjectVersion.get(bucket_id, master_key)
        tags = master.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert master.key == master_key
        assert str(master.version_id) == data['version_id']
        assert master.file
        assert master.file.size == video_size

        # Check metadata tags
        metadata_keys = ['duration', 'bit_rate', 'size', 'avg_frame_rate',
                         'codec_name', 'codec_long_name', 'width', 'height',
                         'nb_frames', 'display_aspect_ratio', 'color_range']
        assert all([key in tags for key in metadata_keys])
        assert ObjectVersion.query.count() == get_object_count()
        assert ObjectVersionTag.query.count() == get_tag_count(is_local=True)

        # Check metadata patch
        recid = PersistentIdentifier.get('depid', video_1_depid).object_uuid
        record = Record.get_record(recid)
        assert 'extracted_metadata' in record['_cds']
        assert all([key in str(record['_cds']['extracted_metadata'])
                    for key in metadata_keys])

        # Check slaves
        for slave_key in slave_keys:
            slave = ObjectVersion.get(bucket_id, slave_key)
            tags = slave.get_tags()
            assert slave.key == slave_key
            assert '_sorenson_job_id' in tags
            assert tags['_sorenson_job_id'] == '1234'
            assert 'master' in tags
            assert tags['master'] == str(master.version_id)
            assert master.file
            assert master.file.size == video_size

        video = deposit_video_resolver(video_1_depid)
        events = get_deposit_events(video['_deposit']['id'])

        # check deposit tasks status
        tasks_status = get_tasks_status_by_task(events)
        assert len(tasks_status) == 3
        assert 'file_transcode' in tasks_status
        assert 'file_video_extract_frames' in tasks_status
        assert 'file_video_metadata_extraction' in tasks_status

        # check single status
        collector = CollectInfoTasks()
        iterate_events_results(events=events, fun=collector)
        info = list(collector)
        assert len(info) == 11
        assert info[0][0] == 'file_video_metadata_extraction'
        assert info[0][1].status == states.SUCCESS
        assert info[1][0] == 'file_video_extract_frames'
        assert info[1][1].status == states.SUCCESS
        transocode_tasks = info[2:]
        statuses = [task[1].status for task in info[2:]]
        assert len(transocode_tasks) == len(statuses)
        assert [states.SUCCESS, states.REVOKED, states.REVOKED, states.REVOKED,
                states.SUCCESS, states.REVOKED, states.REVOKED, states.REVOKED,
                states.REVOKED] == statuses

        # check tags (exclude 'uri-origin')
        assert ObjectVersionTag.query.count() == (get_tag_count() - 1)

        deposit = deposit_video_resolver(video_1_depid)

        # check ElasticSearch is called
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert video_1_id in ids
        assert project_id in ids
        assert deposit['_cds']['state'] == {
            'file_video_metadata_extraction': states.SUCCESS,
            'file_video_extract_frames': states.SUCCESS,
            'file_transcode': states.SUCCESS,
        }

    # Test cleaning!
    url = '{0}?access_token={1}'.format(data['links']['cancel'], access_token)

    with mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:
        # [[ DELETE WORKFLOW ]]
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 201

        # check that object versions and tags are deleted
        # (Create + Delete) * Num Objs - 1 (because the file is local and will
        # be not touched)
        assert ObjectVersion.query.count() == 2 * get_object_count() - 1
        # Tags associated with the old version
        assert ObjectVersionTag.query.count() == get_tag_count(is_local=True)
        bucket = Bucket.query.first()
        # and bucket is empty
        assert bucket.size == 0

        record = RecordMetadata.query.filter_by(id=video_1_id).one()

        # check metadata patch are deleted
        assert 'extracted_metadata' not in record.json['_cds']

        # check the corresponding Event persisted after cleaning
        assert len(get_deposit_events(record.json['_deposit']['id'])) == 0
        assert len(get_deposit_events(record.json['_deposit']['id'],
                                      _deleted=True)) == 1

        # check no reindexing is fired
        assert mock_indexer.called is False


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_clean_download(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video, webhooks):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

    assert ObjectVersionTag.query.count() == get_tag_count()
    event = Event.query.first()
    # [[ CLEAN DOWNLOAD ]]
    event.receiver.clean_task(event=event, task_name='file_download')

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_cds']

    # Create + Clean 1 Download File
    assert ObjectVersion.query.count() == get_object_count() + 1
    assert ObjectVersionTag.query.count() == get_tag_count()

    # RUN again first step
    event.receiver._init_object_version(event=event)
    event.receiver._first_step(event=event).apply()

    # Create + Clean 1 Download File + Run First Step
    assert ObjectVersion.query.count() == get_object_count() + 2
    assert ObjectVersionTag.query.count() == (
        get_tag_count() + get_tag_count(frames=False, transcode=False)
    )


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_clean_video_frames(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video, webhooks):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    event = Event.query.first()
    # [[ CLEAN VIDEO EXTRACT FRAMES ]]
    event.receiver.clean_task(
        event=event, task_name='file_video_extract_frames')

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_cds']

    # Create + Clean Frames
    assert ObjectVersion.query.count() == (
        get_object_count() + get_object_count(download=False, transcode=False)
    )
    assert ObjectVersionTag.query.count() == get_tag_count()

    # RUN again frame extraction
    event.receiver.run_task(
        event=event, task_name='file_video_extract_frames').apply()

    # Create + Clean Frames + Restart Frames
    assert ObjectVersion.query.count() == (
        get_object_count() +
        2 * get_object_count(download=False, transcode=False)
    )
    assert ObjectVersionTag.query.count() == (
        get_tag_count() +
        get_tag_count(download=False, metadata=False, transcode=False)
    )


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_clean_video_transcode(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video, webhooks):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    #
    # CLEAN
    #
    presets = [p for p in get_presets_applied() if p != '1024p']
    for i, preset_quality in enumerate(presets, 1):
        # Clean transcode task for each preset
        event = Event.query.first()
        event.receiver.clean_task(event=event, task_name='file_transcode',
                                  preset_quality=preset_quality)

        # check extracted metadata is there
        records = RecordMetadata.query.all()
        assert len(records) == 1
        assert 'extracted_metadata' in records[0].json['_cds']

        # Create + Delete i-th transcoded files
        assert ObjectVersion.query.count() == get_object_count() + i
        assert ObjectVersionTag.query.count() == get_tag_count()

    # Create + Delete transcoded files
    assert ObjectVersion.query.count() == get_object_count() + len(presets)
    assert ObjectVersionTag.query.count() == get_tag_count()

    #
    # RUN again
    #
    for i, preset_quality in enumerate(presets, 1):
        event = Event.query.first()
        event.receiver.run_task(event=event, task_name='file_transcode',
                                preset_quality=preset_quality).apply()

        # Create + Delete transcoded files + Restart i-th transcode
        assert ObjectVersion.query.count() == (
            get_object_count() + len(presets) + i
        )
        # if changed, copy magic number 14 from helpers::get_tag_count
        assert ObjectVersionTag.query.count() == get_tag_count() + (i * 14)


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_clean_extract_metadata(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video, webhooks):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        # [[ RUN ]]
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    # [[ CLEAN VIDEO METADATA EXTRACTION ]]
    event = Event.query.first()
    event.receiver.clean_task(
        event=event, task_name='file_video_metadata_extraction')

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' not in records[0].json['_cds']

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    # [[ RUN again metadata extraction ]]
    event.receiver.run_task(
        event=event, task_name='file_video_metadata_extraction').apply()

    # Metadata Extraction doesn't create new objects
    assert ObjectVersion.query.count() == get_object_count()
    # neither new tags, but update the current
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_cds']


@pytest.mark.parametrize(
    'receiver_id, workflow, status, http_status, payload, result', [
        ('failing-task', failing_task, states.FAILURE, 500, {}, None),
        ('success-task', success_task, states.SUCCESS, 201, {}, None),
        ('add-task', simple_add, states.SUCCESS, 202, {'x': 40, 'y': 2}, 42)
    ]
)
def test_async_receiver_status_fail(api_app, access_token, u_email,
                                    json_headers, receiver_id, workflow,
                                    status, http_status, payload, result):
    """Test AVC workflow test-case."""
    ctx = dict()

    class TestReceiver(CeleryAsyncReceiver):

        def run(self, event):
            assert payload == event.payload
            ctx['myresult'] = workflow.s(**event.payload).apply_async()
            self._serialize_result(event=event, result=ctx['myresult'])
            super(TestReceiver, self).persist(
                event=event, result=ctx['myresult'])

        def _raw_info(self, event):
            result = self._deserialize_result(event)
            return {receiver_id: result}

    current_webhooks.register(receiver_id, TestReceiver)

    with api_app.test_request_context():
        url = url_for('invenio_webhooks.event_list',
                      receiver_id=receiver_id,
                      access_token=access_token)
    with api_app.test_client() as client:
        # run the task
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == http_status
        data = json.loads(resp.headers['X-Hub-Info'])
        assert data['name'] == receiver_id
        extra_info = json.loads(resp.headers['X-Hub-Info'])
        assert extra_info['id'] == ctx['myresult'].id
        assert ctx['myresult'].result == result

    with api_app.test_request_context():
        event_id = resp.headers['X-Hub-Delivery']
        url = url_for('invenio_webhooks.event_item',
                      receiver_id=receiver_id, event_id=event_id,
                      access_token=access_token)
    with api_app.test_client() as client:
        # check status
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == http_status
        data = json.loads(resp.headers['X-Hub-Info'])
        #  assert data['status'] == status
        assert data['name'] == receiver_id
        extra_info = json.loads(resp.headers['X-Hub-Info'])
        assert extra_info['id'] == ctx['myresult'].id


def test_collect_info():
    """Test info extractor."""
    result = simple_add.s(1, 2).apply_async()

    info = collect_info('mytask', result)
    assert info['status'] == states.SUCCESS
    assert info['info'] == 3
    assert 'id' in info
    assert info['name'] == 'mytask'

    result = chain(simple_add.s(1, 2), simple_add.s(3)).apply_async()

    # check first task
    info = collect_info('mytask', result.parent)
    assert info['status'] == states.SUCCESS
    assert info['info'] == 3
    assert 'id' in info
    assert info['name'] == 'mytask'
    # check second task
    info = collect_info('mytask2', result)
    assert info['status'] == states.SUCCESS
    assert info['info'] == 6
    assert 'id' in info
    assert info['name'] == 'mytask2'

    result = chain(
        simple_add.s(1, 2),
        group(simple_add.s(3), simple_add.s(4), failing_task.s())
    ).apply_async()

    info = collect_info('mytask', result.parent)
    assert info['status'] == states.SUCCESS
    assert info['info'] == 3
    assert 'id' in info
    assert info['name'] == 'mytask'

    info = collect_info('mytask2', result.children[0])
    assert info['status'] == states.SUCCESS
    assert info['info'] == 6
    assert 'id' in info
    assert info['name'] == 'mytask2'

    info = collect_info('mytask3', result.children[1])
    assert info['status'] == states.SUCCESS
    assert info['info'] == 7
    assert 'id' in info
    assert info['name'] == 'mytask3'

    fail = AsyncResult(result.children[2].id)
    info = collect_info('mytask4', fail)
    assert info['status'] == states.FAILURE
    assert 'id' in info
    assert info['name'] == 'mytask4'


def test_serializer():
    """Test result serializer on event."""
    event = Event()
    event.response = {}
    event.response_headers = {}

    result = chain(
        simple_add.s(1, 2),
        group(simple_add.s(3), simple_add.s(4), failing_task.s())
    ).apply_async()

    CeleryAsyncReceiver._serialize_result(event=event, result=result)
    deserialized_result = CeleryAsyncReceiver._deserialize_result(event=event)

    assert deserialized_result.id == result.id
    assert deserialized_result.parent.id == result.parent.id
    assert deserialized_result.children[0].id == result.children[0].id
    assert deserialized_result.children[1].id == result.children[1].id
    assert deserialized_result.children[2].id == result.children[2].id
