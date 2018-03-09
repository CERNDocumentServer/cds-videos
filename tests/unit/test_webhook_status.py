# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""CDS tests for Webhook status."""

from __future__ import absolute_import

import mock
import json
from celery import states
from copy import deepcopy
from flask import url_for
from collections import namedtuple
from cds.modules.webhooks.status import GetInfoByID, iterate_result, \
    CollectStatusesByTask, merge_tasks_status, get_tasks_status_by_task, \
    _compute_status
from invenio_webhooks.models import Event
from helpers import mock_current_user


@mock.patch('flask_login.current_user', mock_current_user)
def test_tasks_status(api_app, db, bucket, cds_depid,
                      access_token, json_headers, mock_sorenson,
                      online_video, webhooks):
    """Test status of tasks."""
    db.session.add(bucket)
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
            bucket_id=str(bucket.id),
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 201

        data = json.loads(resp.data.decode('utf-8'))
        event = Event.query.first()
        status = data['global_status']
        for group in status:
            for task in group:
                task_name, info = next(iter(task.items()))
                task_id = info['id']
                search = GetInfoByID(task_id=task_id)
                iterate_result(raw_info=event.receiver._raw_info(event=event),
                               fun=search)
                assert search.task_name == task_name


def test_collect_statuses_by_task():
    """Test CollectStatusesByTask."""
    AsyncResult = namedtuple('AsyncResult', ['result', 'status'])

    coll = CollectStatusesByTask(statuses={
        'file_download': states.PENDING,
    })
    # simulate a task start
    coll('file_transcode', AsyncResult(status=states.STARTED, result={}))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.STARTED,
    }
    # simulate the redis cache for celery tasks is cleanup
    coll('file_transcode', AsyncResult(status=states.FAILURE, result=None))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.STARTED,
    }
    # simulate a task is failing
    coll('file_transcode', AsyncResult(status=states.FAILURE, result={}))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.FAILURE,
    }
    # simulate db empty and celery tasks is cleanup
    coll = CollectStatusesByTask(statuses={})
    coll('file_download', AsyncResult(status=states.FAILURE, result=None))
    assert coll.statuses == {}

    # simulate that we run the tasks and the result is:
    #    1 transcode fail + 1 transcode success = fail
    # we save them in db:
    db_status = {
        'file_download': states.PENDING,
        'file_transcode': states.FAILURE,
    }
    # now we ask the current status:
    coll = CollectStatusesByTask(statuses=deepcopy(db_status))
    assert coll.statuses == db_status
    # we update it because the failing transcode is restarted
    coll('file_transcode', AsyncResult(status=states.STARTED, result={}))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.STARTED,
    }
    # we clean the celery cache and try to read the up-to-date tasks status
    coll('file_transcode', AsyncResult(status=states.PENDING, result=None))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.STARTED,
    }
    # we update the db informations
    db_status = deepcopy(coll.statuses)
    # now we restart again the task and it's successfully finish the job
    coll = CollectStatusesByTask(statuses=db_status)
    coll('file_transcode', AsyncResult(status=states.SUCCESS, result={}))
    assert coll.statuses == {
        'file_download': states.PENDING,
        'file_transcode': states.SUCCESS,
    }


def test_get_tasks_status_by_task():
    """Test get tasks status by task."""
    # simulate a "celery cache empty" creating an empty result
    AsyncResult = namedtuple('AsyncResult', ['result', 'status'])
    lost_result = AsyncResult(None, states.PENDING)
    # and: event -> receiver -> lost result
    Event = namedtuple('Event', ['receiver'])
    receiver = mock.MagicMock()
    receiver.has_result = mock.MagicMock(return_value=True)
    receiver._raw_info = mock.MagicMock(
        return_value={'task_trascode': lost_result})
    event = Event(receiver)
    # build the current state if the previous value saved on db is SUCCESS
    computed_states = get_tasks_status_by_task(
        events=[event], statuses={'task_trascode': states.SUCCESS})
    assert computed_states == {'task_trascode': states.SUCCESS}


def test_merge_tasks_status():
    """Test merge tasks status."""
    statuses_1 = {
        'task_download': states.STARTED,
        'task_metadata_extraction': states.SUCCESS,
    }
    statuses_2 = {
        'task_frame_extraction': states.FAILURE,
        'task_metadata_extraction': states.PENDING,
    }
    assert {
        'task_download': states.STARTED,
        'task_metadata_extraction': states.PENDING,
        'task_frame_extraction': states.FAILURE,
    } == merge_tasks_status(statuses_1, statuses_2)


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
    assert states.SUCCESS == _compute_status([
        states.SUCCESS, states.REVOKED, states.SUCCESS, states.SUCCESS])
    assert states.SUCCESS == _compute_status([states.SUCCESS, states.SUCCESS])
    assert states.REVOKED == _compute_status([states.REVOKED, states.REVOKED])
    assert None is _compute_status([None, None])
