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
from time import sleep

import mock
from flask import url_for

from invenio_files_rest.models import ObjectVersion
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record


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
            api_app.test_client() as client:
        mock_request.return_value = type('Response', (object, ),
                                         {'content': b'\x00' * 1024})
        payload = dict(
            uri='http://example.com/test.pdf',
            bucket_id=str(bucket.id),
            deposit_id=depid,
            key='test.pdf')
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
        assert obj.file.size == 1024

        # TODO get status after POST


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

        assert ObjectVersion.query.count() == 2
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
        assert 'job_id' in tags
        assert tags['job_id'] == '1234'
        assert 'master' in tags
        assert tags['master'] == str(master.version_id)
        assert slave.key == 'test-Youtube 480p.mp4'
        assert master.file
        assert master.file.size == video_size
