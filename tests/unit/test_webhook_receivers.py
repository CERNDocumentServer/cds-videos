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
