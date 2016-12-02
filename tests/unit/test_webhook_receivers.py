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

from invenio_files_rest.models import ObjectVersion, as_object_version
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
import pytest

from celery import states, chain, group
from celery.result import AsyncResult
from invenio_webhooks import current_webhooks
from cds.modules.deposit.api import video_resolver, cds_resolver
from cds.modules.webhooks.status import _compute_status, collect_info, \
    get_tasks_status_by_task, get_deposit_events, iterate_events_results
from cds.modules.webhooks.receivers import CeleryAsyncReceiver
from cds.modules.webhooks.status import CollectInfoTasks
from invenio_webhooks.models import Event
from six import BytesIO

from helpers import failing_task, simple_add, mock_current_user


@mock.patch('flask_login.current_user', mock_current_user)
def test_download_receiver(api_app, db, bucket, cds_depid, access_token,
                           json_headers, webhooks):
    """Test downloader receiver."""
    db.session.add(bucket)
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='downloader',
            access_token=access_token)

    with mock.patch('requests.get') as mock_request, \
            mock.patch('invenio_sse.ext._SSEState.publish') as mock_sse, \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_indexer, \
            api_app.test_client() as client:

        sse_channel = 'mychannel'
        mock_sse.return_value = None

        file_size = 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })

        payload = dict(
            uri='http://example.com/test.pdf',
            bucket_id=str(bucket.id),
            deposit_id=cds_depid,
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
                        'deposit_id': cds_depid,
                        'percentage': percentage,
                        'version_id': str(obj.version_id),
                        'size': size,
                        'total': total,
                    }
                }
            }
        assert mock_sse.call_count == 4
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
        deposit = cds_resolver([cds_depid])[0]
        mock_sse.assert_any_call(
            channel='mychannel',
            data={
                'state': states.SUCCESS,
                'meta': {
                    'payload': {
                        'event_id': str(tags['_event_id']),
                        'deposit_id': cds_depid,
                        'deposit': deposit,
                    }
                }
            },
            type_='update_deposit',
        )

        # check ElasticSearch is called
        args, kwargs = mock_indexer.call_args
        (arg,) = args
        deposit_to_index = next(arg)
        assert str(deposit.id) == deposit_to_index
        assert deposit['_deposit']['state'] == {u'file_download': u'STARTED'}


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver(api_app, db, bucket, cds_depid, access_token,
                               json_headers, mock_sorenson, online_video,
                               webhooks):
    """Test AVCWorkflow receiver."""
    db.session.add(bucket)
    bucket_id = bucket.id
    video_size = 5510872
    master_key = 'test.mp4'
    slave_key1 = 'test-Youtube 480p.mp4'
    slave_key2 = 'test-Youtube 720p.mp4'
    with api_app.test_request_context():
        url = url_for(
            'invenio_webhooks.event_list',
            receiver_id='avc',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_sse.ext._SSEState.publish') as mock_sse, \
            mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_indexer:
        sse_channel = 'mychannel'
        payload = dict(
            uri=online_video,
            bucket_id=str(bucket.id),
            deposit_id=cds_depid,
            key=master_key,
            sse_channel=sse_channel
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 202
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == online_video
        assert data['key'] == master_key
        assert 'version_id' in data
        assert 'links' in data  # TODO decide with links are needed

        # 1 original + 2 slave + 90 frames == 93
        assert ObjectVersion.query.count() == 93

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
        recid = PersistentIdentifier.get('depid', cds_depid).object_uuid
        record = Record.get_record(recid)
        assert 'extracted_metadata' in record['_deposit']
        assert all([key in str(record['_deposit']['extracted_metadata'])
                    for key in metadata_keys])

        # Slave file 1
        slave = ObjectVersion.get(bucket_id, slave_key1)
        tags = slave.get_tags()
        assert '_sorenson_job_id' in tags
        assert tags['_sorenson_job_id'] == '1234'
        assert 'master' in tags
        assert tags['master'] == str(master.version_id)
        assert slave.key == 'test-Youtube 480p.mp4'
        assert master.file
        assert master.file.size == video_size

        # Slave file 2
        slave = ObjectVersion.get(bucket_id, slave_key2)
        tags = slave.get_tags()
        assert '_sorenson_job_id' in tags
        assert tags['_sorenson_job_id'] == '1234'
        assert 'master' in tags
        assert tags['master'] == str(master.version_id)
        assert slave.key == 'test-Youtube 720p.mp4'
        assert master.file
        assert master.file.size == video_size

        video = video_resolver([cds_depid])[0]
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
        assert info[0][0] == 'file_download'
        assert info[0][1].status == states.STARTED
        assert info[1][0] == 'file_video_metadata_extraction'
        assert info[1][1].status == states.SUCCESS
        assert info[2][0] == 'file_video_extract_frames'
        assert info[2][1].status == states.STARTED
        assert info[3][0] == 'file_transcode'
        assert info[3][1].status == states.STARTED
        assert info[4][0] == 'file_transcode'
        assert info[4][1].status == states.STARTED

        # check sse is called
        assert mock_sse.called

        messages = [
            (sse_channel, states.STARTED, 'file_download'),
            (sse_channel, states.SUCCESS, 'file_download'),
            (sse_channel, states.SUCCESS, 'file_video_metadata_extraction'),
            (sse_channel, states.STARTED, 'file_transcode'),
            (sse_channel, states.SUCCESS, 'file_transcode'),
            (sse_channel, states.STARTED, 'file_video_extract_frames'),
            (sse_channel, states.SUCCESS, 'file_video_extract_frames'),
            (sse_channel, states.SUCCESS, 'update_deposit'),
        ]

        call_args = []
        for (_, kwargs) in mock_sse.call_args_list:
            type_ = kwargs['type_']
            state = kwargs['data']['state']
            channel = kwargs['channel']
            tuple_ = (channel, state, type_)
            if tuple_ not in call_args:
                call_args.append(tuple_)

        assert len(call_args) == len(messages)
        for message in messages:
            assert message in call_args

        deposit = cds_resolver([cds_depid])[0]

        def filter_events(call_args):
            _, x = call_args
            return x['type_'] == 'update_deposit'

        list_kwargs = list(filter(filter_events, mock_sse.call_args_list))
        assert len(list_kwargs) == 1
        _, kwargs = list_kwargs[0]
        kwargs['type_'] == 'update_deposit'
        kwargs['channel'] == 'mychannel'
        kwargs['data']['state'] == states.SUCCESS
        kwargs['data']['meta']['payload'] == {
            'deposit_id': deposit['_deposit']['id'],
            'event_id': data['tags']['_event_id'],
            'deposit': deposit,
        }

        # check ElasticSearch is called
        args, kwargs = mock_indexer.call_args
        (arg,) = args
        deposit_to_index = next(arg)
        assert str(deposit.id) == deposit_to_index
        assert deposit['_deposit']['state'] == {
            'file_download': states.STARTED,
            'file_video_metadata_extraction': states.SUCCESS,
            'file_video_extract_frames': states.STARTED,
            'file_transcode': states.STARTED,
        }


@pytest.mark.parametrize(
    'receiver_id,workflow,status,http_status, payload,result', [
        #  ('failing-task', failing_task, states.FAILURE, 500, {}, None),
        #  ('success-task', success_task, states.SUCCESS, 201, {}, None),
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


def test_collect_info():
    """Test info extractor."""
    result = simple_add.s(1, 2).apply_async()

    info = collect_info('mytask', result)
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'

    result = chain(simple_add.s(1, 2), simple_add.s(3)).apply_async()

    # check first task
    info = collect_info('mytask', result.parent)
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'
    # check second task
    info = collect_info('mytask2', result)
    assert info['status'] == states.SUCCESS
    assert info['info'] == '6'
    assert 'id' in info
    assert info['name'] == 'mytask2'
    assert info['result'] == '6'

    result = chain(
        simple_add.s(1, 2),
        group(simple_add.s(3), simple_add.s(4), failing_task.s())
    ).apply_async()

    info = collect_info('mytask', result.parent)
    assert info['status'] == states.SUCCESS
    assert info['info'] == '3'
    assert 'id' in info
    assert info['name'] == 'mytask'
    assert info['result'] == '3'

    info = collect_info('mytask2', result.children[0])
    assert info['status'] == states.SUCCESS
    assert info['info'] == '6'
    assert 'id' in info
    assert info['name'] == 'mytask2'
    assert info['result'] == '6'

    info = collect_info('mytask3', result.children[1])
    assert info['status'] == states.SUCCESS
    assert info['info'] == '7'
    assert 'id' in info
    assert info['name'] == 'mytask3'
    assert info['result'] == '7'

    fail = AsyncResult(result.children[2].id)
    info = collect_info('mytask4', fail)
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
