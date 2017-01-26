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
from flask import url_for
from cds.modules.webhooks.status import GetInfoByID, iterate_result
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
        sse_channel = 'mychannel'
        payload = dict(
            uri=online_video,
            bucket_id=str(bucket.id),
            deposit_id=cds_depid,
            key=master_key,
            sse_channel=sse_channel,
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
