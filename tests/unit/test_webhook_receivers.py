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

from celery import states
from celery.result import AsyncResult
from flask import url_for
from os.path import commonprefix

from invenio_accounts.testutils import login_user_via_session


def make_request(app, receiver_id, access_token, u_email, payload, check_func):
    """Make a POST request to a webhook receiver with given payload."""
    # Get webhook URLs
    with app.test_request_context():
        url_1 = url_for('invenio_webhooks.event_list', receiver_id=receiver_id,
                        access_token=access_token)
        url_2 = url_for('cds_webhooks.event_list', receiver_id=receiver_id)

    # Make POST requests
    headers = [('Content-Type', 'application/json')]
    with app.test_client() as client:
        # Invenio-Webhooks view, which uses OAuth access token
        resp_1 = client.post(url_1, headers=headers, data=json.dumps(payload))

        # CDS-Webhooks view, which uses current_user in session
        login_user_via_session(client, email=u_email)
        resp_2 = client.post(url_2, headers=headers, data=json.dumps(payload))

        assert resp_1.status_code == resp_2.status_code

        # Extract data from responses
        resp_1 = json.loads(resp_1.get_data(as_text=True))
        resp_2 = json.loads(resp_2.get_data(as_text=True))

        # Check both responses with given `check_func`
        assert resp_1.keys() == resp_2.keys()
        check_func(resp_1)
        check_func(resp_2)


def test_add(api_app, receiver, access_token, u_email):
    """Test AVC workflow test-case."""
    payload = {'x': 40, 'y': 2}

    def check(resp):
        assert resp['status'] == 202
        assert resp['message'] == 42

    make_request(api_app, receiver, access_token, u_email, payload, check)


def test_downloader(api_app, db, bucket, access_token, online_video, u_email):
    """Test Downloader receiver."""
    db.session.add(bucket)
    bucket_dir = bucket.location.uri
    payload = dict(
        url=online_video,
        bucket_id=str(bucket.id),
        chunk_size=5242880,
    )

    def check(resp):
        assert 'event_id' in resp
        assert resp['status'] == 202
        file_loc = resp['message']
        assert commonprefix([file_loc, bucket_dir]) == bucket_dir

    make_request(api_app, 'downloader', access_token, u_email, payload, check)


def test_metadata(api_app, video_mov, access_token, u_email):
    """Test VideoMetadataExtractor receiver."""
    payload = {'video_location': video_mov}

    def check(resp):
        assert 'event_id' in resp
        assert resp['status'] == 202
        msg = resp['message']

        assert 'format' in msg
        assert 'duration' in msg['format']
        assert float(msg['format']['duration']) == 15.459
        assert 'filename' in msg['format']
        assert msg['format']['filename'] == video_mov

        assert 'streams' in msg
        assert 'codec_name' in msg['streams'][0]
        assert msg['streams'][0]['codec_name'] == 'h264'
        assert 'codec_type' in msg['streams'][0]
        assert msg['streams'][0]['codec_type'] == 'video'

    make_request(api_app, 'metadata', access_token, u_email, payload, check)


def test_avc(api_app, db, bucket, online_video, depid,
             access_token, mock_sorenson, u_email):
    """Test AVCWorkflow receiver."""
    db.session.add(bucket)
    payload = dict(
        dep_id=depid,

        url=online_video,
        bucket_id=str(bucket.id),
        chunk_size=5242880,

        preset_name='Youtube 480p',

        start_percentage=5,
        end_percentage=95,
        number_of_frames=10,
        size_percentage=5,
        output_folder=bucket.location.uri,
    )

    def check(resp):
        assert 'event_id' in resp
        event_id = resp['event_id']
        assert resp['status'] == 202

        # Check progress report on Celery backend
        result = AsyncResult(event_id)
        (state, meta) = result.state, result.info or {}

        assert state == states.STARTED
        for task in ['download', 'transcode', 'extract_frames',
                     'attach_files']:
            assert task in meta
            assert 'order' in meta[task]
            assert 'percentage' in meta[task]
            assert meta[task]['percentage'] == 100

    make_request(api_app, 'avc', access_token, u_email, payload, check)
