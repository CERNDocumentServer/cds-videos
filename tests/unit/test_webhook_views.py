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
from flask import url_for
from helpers import mock_current_user
from invenio_files_rest.models import ObjectVersion, \
    ObjectVersionTag, Bucket
from invenio_records.models import RecordMetadata


def check_video_transcode(api_app, event_id, access_token,
                          json_headers, data):
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

    # 1 master + 1 slave + 90 frames == 92
    assert ObjectVersion.query.count() == 92

    # check tags
    assert ObjectVersionTag.query.count() == 196

    # check extracted metadata is not there
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

    # 1 master + 90 frames == 91
    assert ObjectVersion.query.count() == 91

    # check tags
    assert ObjectVersionTag.query.count() == 192

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check bucket size
    bucket = Bucket.query.first()
    assert bucket.size == 0


def check_video_frames(api_app, event_id, access_token,
                       json_headers, data):
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

    # 1 master + 2 slave == 3
    assert ObjectVersion.query.count() == 3

    # check tags
    assert ObjectVersionTag.query.count() == 20

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check bucket size
    bucket = Bucket.query.first()
    assert bucket.size == 0


def check_video_download(api_app, event_id, access_token,
                         json_headers, data):
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

    # 2 slave + 90 frames == 92
    assert ObjectVersion.query.count() == 92

    # check tags
    assert ObjectVersionTag.query.count() == 188

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check bucket size
    bucket = Bucket.query.first()
    assert bucket.size == 0


def check_video_metadata_extraction(api_app, event_id, access_token,
                                    json_headers, data):
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

    # 1 master + 2 slave + 90 frames == 93
    assert ObjectVersion.query.count() == 93

    # check tags
    assert ObjectVersionTag.query.count() == 190

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' not in records[0].json['_deposit']


@pytest.mark.parametrize('checker', [
    check_video_metadata_extraction,
    check_video_download,
    check_video_frames,
    check_video_transcode
])
@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_delete(api_app, db, bucket, cds_depid,
                             access_token, json_headers, mock_sorenson,
                             online_video, webhooks, checker):
    """Test AVCWorkflow receiver."""
    db.session.add(bucket)
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
            bucket_id=str(bucket.id),
            deposit_id=cds_depid,
            key=master_key,
            sse_channel=sse_channel
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201
        data = json.loads(resp.data.decode('utf-8'))

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_deposit']

    # check object versions don't change:
    # 1 original + 2 slave + 90 frames == 93
    assert ObjectVersion.query.count() == 93

    # check tags
    assert ObjectVersionTag.query.count() == 200

    event_id = data['tags']['_event_id']
    ###
    checker(api_app, event_id, access_token, json_headers, data)
