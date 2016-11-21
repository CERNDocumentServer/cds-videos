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

"""CDS tests for Webhook receivers."""

from __future__ import absolute_import, print_function

import json

import mock
from flask import url_for

from invenio_files_rest.models import ObjectVersion
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
import pytest

from celery import states, chain, group
from celery.result import AsyncResult
from cds.modules.webhooks.receivers import CeleryAsyncReceiver
from invenio_webhooks import current_webhooks
from cds.modules.webhooks.receivers import _compute_status
from cds.modules.webhooks.receivers import _info_extractor
from invenio_webhooks.models import Event

from helpers import failing_task, success_task, simple_add


def test_download_receiver(api_app, db, bucket, depid, access_token,
                           json_headers):
    """Test downloader receiver."""
    db.session.add(bucket)
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            mock.patch('invenio_sse.ext._SSEState.publish') as mock_sse, \
            api_app.test_client() as client:

        sse_channel = 'mychannel'
        mock_sse.return_value = None

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
            key='test.pdf',
            sse_channel=sse_channel
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 202
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == 'http://example.com/test.pdf'
        assert data['key'] == 'test.pdf'
        assert 'version_id' in data
        assert 'links' in data  # TODO decide with links are needed

        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        tags = obj.get_tags()
        assert tags['_event_id'] == data['tags']['_event_id']
        assert obj.key == data['key']
        assert str(obj.version_id) == data['version_id']
        assert obj.file
        assert obj.file.size == file_size

        # check sse is called
        assert mock_sse.called

        def set_data(state, message, size, total, percentage):
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
                        },
                        'deposit_id': depid,
                        'percentage': percentage,
                        'version_id': str(obj.version_id),
                        'size': size,
                        'total': total,
                    }
                }
            }
        assert mock_sse.call_count == 3
        mock_sse.assert_any_call(
            data=set_data(
                states.STARTED,
                'Downloading {} of {}'.format(file_size, file_size),
                file_size, file_size, 100
            ),
            channel=u'mychannel',
            type_='file_download'
        )
        mock_sse.assert_any_call(
            data=set_data(
                states.SUCCESS, str(obj.version_id), file_size, file_size, 100
            ),
            channel=u'mychannel',
            type_='file_download'
        )


def test_avc_workflow_receiver(api_app, db, bucket, depid, access_token,
                               json_headers, mock_sorenson, online_video):
    """Test AVCWorkflow receiver."""
    db.session.add(bucket)
    bucket_id = bucket.id
    video_size = 5510872
    master_key, slave_key = 'test.mp4', 'test-Youtube 480p.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            bucket_id=str(bucket.id),
            deposit_id=depid,
            key=master_key,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 202
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == online_video
        assert data['key'] == master_key
        assert 'version_id' in data
        assert 'links' in data  # TODO decide with links are needed

        # 1 original + 1 slave + 90 frames == 92
        assert ObjectVersion.query.count() == 92

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
                         'codec_name', 'width', 'height', 'nb_frames',
                         'display_aspect_ratio', 'color_range']
        assert all([key in tags for key in metadata_keys])

        # Check metadata patch
        recid = PersistentIdentifier.get('depid', depid).object_uuid
        record = Record.get_record(recid)
        assert 'extracted_metadata' in record['_deposit']
        assert all([key in str(record['_deposit']['extracted_metadata'])
                    for key in metadata_keys])

        # Slave file
        slave = ObjectVersion.get(bucket_id, slave_key)
        tags = slave.get_tags()
        assert '_sorenson_job_id' in tags
        assert tags['_sorenson_job_id'] == '1234'
        assert 'master' in tags
        assert tags['master'] == str(master.version_id)
        assert slave.key == 'test-Youtube 480p.mp4'
        assert master.file
        assert master.file.size == video_size


@pytest.mark.parametrize(
    'receiver_id,workflow,status,http_status, payload,result', [
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
            self._serialize_result(event, ctx['myresult'])

        def _status_and_info(self, event):
            result = self._deserialize_result(event)
            status = result.status
            info = _info_extractor(result, receiver_id)
            return dict(status=status, info=info)

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


def test_compute_status():
    """Test compute status."""
    assert states.FAILURE == _compute_status([
        states.STARTED, states.RETRY, states.PENDING, states.FAILURE,
        states.SUCCESS])
    assert states.STARTED == _compute_status([
        states.RETRY, states.PENDING, states.STARTED, states.SUCCESS])
    assert states.RETRY == _compute_status([
        states.RETRY, states.PENDING, states.SUCCESS, states.SUCCESS])
    assert states.PENDING == _compute_status([
        states.PENDING, states.PENDING, states.SUCCESS, states.SUCCESS])
    assert states.SUCCESS == _compute_status([states.SUCCESS, states.SUCCESS])


def test_info_extractor():
    """Test info extractor."""
    result = simple_add.s(1, 2).apply_async()

    info = _info_extractor(result, 'mytask')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'

    result = chain(simple_add.s(1, 2), simple_add.s(3)).apply_async()

    # check first task
    info = _info_extractor(result.parent, 'mytask')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'
    # check second task
    info = _info_extractor(result, 'mytask2')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '6'
    assert 'id' in info
    assert info['name'] == 'mytask2'
    assert info['result'] == '6'

    result = chain(
        simple_add.s(1, 2),
        group(simple_add.s(3), simple_add.s(4), failing_task.s())
    ).apply_async()

    info = _info_extractor(result.parent, 'mytask')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'

    info = _info_extractor(result.children[0], 'mytask2')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '6'
    assert 'id' in info
    assert info['name'] == 'mytask2'
    assert info['result'] == '6'

    info = _info_extractor(result.children[1], 'mytask3')
    assert info['status'] == states.SUCCESS
    assert info['info'] == '7'
    assert 'id' in info
    assert info['name'] == 'mytask3'
    assert info['result'] == '7'

    fail = AsyncResult(result.children[2].id)
    info = _info_extractor(fail, 'mytask4')
    assert info['status'] == states.FAILURE
    assert 'id' in info
    assert info['name'] == 'mytask4'


def test_serializer():
    """Test result serializer on event."""
    event = Event()
    event.response = {}

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
