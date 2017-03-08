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
from flask import url_for
from helpers import get_object_count, get_tag_count, mock_current_user
from invenio_files_rest.models import ObjectVersion, \
    ObjectVersionTag, Bucket
from invenio_records.models import RecordMetadata
from six import BytesIO
from cds.modules.deposit.api import video_resolver
from invenio_webhooks.models import Event

from helpers import get_indexed_records_from_mock


def check_restart_avc_workflow(api_app, event_id, access_token,
                               json_headers, data, video_id):
    """Try to restart AVC workflow via REST API."""
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_item',
            receiver_id='avc',
            event_id=event_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish') as mock_sse, \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_indexer:
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.put(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check SSE
    assert mock_sse.called is True

    # check elasticsearch
    assert mock_indexer.called is True
    ids = get_indexed_records_from_mock(mock_indexer)
    assert len(ids) == 10
    assert set(ids) == set([video_id])


def check_video_transcode_delete(api_app, event_id, access_token,
                                 json_headers, data, video_id):
    """Try to delete transcoded file via REST API."""
    # DELETE FIRST TRANSCODED FILE
    task_id = data['global_status'][1][1]['file_transcode']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.delete(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count() - 1
    assert ObjectVersionTag.query.count() == get_tag_count() - 5

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check bucket size
    bucket = Bucket.query.first()
    assert bucket.size == 0

    # DELETE SECOND TRANSCODED FILE
    task_id = data['global_status'][1][2]['file_transcode']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.delete(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count() - 2
    assert ObjectVersionTag.query.count() == get_tag_count() - 10

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']


def check_video_transcode_restart(api_app, event_id, access_token,
                                  json_headers, data, video_id):
    """Try to delete transcoded file via REST API."""
    # RESTART FIRST TRANSCODED FILE
    task_id = data['global_status'][1][1]['file_transcode']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish') as mock_sse, \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.put(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

        assert mock_sse.called is True

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check task id is changed
    event = Event.query.first()
    new_task_id = event.response['global_status'][1][1]['file_transcode']['id']
    assert task_id != new_task_id
    old_result = AsyncResult(task_id)
    new_result = AsyncResult(new_task_id)
    for key in ['tags', 'key', 'deposit_id', 'event_id', 'preset_quality']:
        assert old_result.result[
            'payload'][key] == new_result.result['payload'][key]


def check_video_frames(api_app, event_id, access_token,
                       json_headers, data, video_id):
    """Try to delete video frames via REST API."""
    task_id = data['global_status'][1][0]['file_video_extract_frames']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.delete(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count(frames=False)
    assert ObjectVersionTag.query.count() == get_tag_count(frames=False)

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']


def check_video_download(api_app, event_id, access_token,
                         json_headers, data, video_id):
    """Try to delete downloaded files via REST API."""
    task_id = data['global_status'][0][0]['file_download']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.delete(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count(download=False)
    assert ObjectVersionTag.query.count() == get_tag_count(download=False)

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']


def check_video_metadata_extraction(api_app, event_id, access_token,
                                    json_headers, data, video_id):
    """Try to delete metadata extraction via REST API."""
    task_id = data['global_status'][0][1][
        'file_video_metadata_extraction']['id']
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.task_item',
            receiver_id='avc',
            event_id=event_id,
            task_id=task_id,
            access_token=access_token
        )
    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            sse_channel=sse_channel
        )
        resp = client.delete(
            url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 204

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count(metadata=False)

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' not in records[0].json['_deposit']


@pytest.mark.parametrize('checker', [
    check_restart_avc_workflow,
    check_video_metadata_extraction,
    check_video_download,
    check_video_frames,
    check_video_transcode_delete,
    check_video_transcode_restart,
])
@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_delete(api_app, db, cds_depid,
                             access_token, json_headers, mock_sorenson,
                             online_video, webhooks, checker):
    """Test AVCWorkflow receiver REST API."""
    master_key = 'test.mp4'

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sse_channel=sse_channel,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    event_id = data['tags']['_event_id']
    video_id = str(video_resolver([cds_depid])[0].id)
    ###
    checker(api_app, event_id, access_token, json_headers, data, video_id)


@mock.patch('flask_login.current_user', mock_current_user)
def test_download_workflow_delete(api_app, db, cds_depid, access_token,
                                  json_headers, mock_sorenson, online_video,
                                  webhooks):
    """Test Download receiver REST API."""
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token
        )

    with mock.patch('requests.get') as mock_request, \
            api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        sse_channel = 'mychannel'
        file_size = 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            deposit_id=cds_depid,
            key='test.pdf',
            sse_channel=sse_channel
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        tags = obj.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert obj.key == data['key']
        assert str(obj.version_id) == data['version_id']
        assert obj.file
        assert obj.file.size == file_size

    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_item',
            receiver_id='downloader',
            event_id=data['tags']['_event_id'],
            access_token=access_token
        )

    with mock.patch('requests.get') as mock_request, \
            api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish'), \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'):
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        resp = client.put(url, headers=json_headers)

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        tags = obj.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert obj.key == data['key']
        assert str(obj.version_id) == data['version_id']
        assert obj.file
        assert obj.file.size == file_size
