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

"""Test cds package."""

from __future__ import absolute_import, print_function

import mock
import json
import uuid

from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_indexer.api import RecordIndexer
from invenio_db import db
from invenio_records.api import Record
from xml.etree import ElementTree as ET
from time import sleep
from flask import url_for
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from cds.modules.deposit.api import Video


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_ui_export(app, project_published):
    """Test view."""
    (project, video_1, video_2) = project_published
    pid = project['_deposit']['pid']['value']
    vid = video_1['_deposit']['pid']['value']
    with app.test_request_context():
        url_no_existing_exporter = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='blabla')
        url_not_valid_type_record = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='smil')
        url_valid_smil = url_for(
            'invenio_records_ui.recid_export', pid_value=vid, format='smil')
        url_valid_json = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='json')

    with app.test_client() as client:
        # Test that default view function can deal with multiple parameters.
        res = client.get(url_no_existing_exporter)
        assert res.status_code == 404
        res = client.get(url_not_valid_type_record)
        assert res.status_code == 400
        res = client.get(url_valid_smil)
        assert res.status_code == 200
        res = client.get(url_valid_json)
        assert res.status_code == 200
        # Test that actual data has been exported (not blank)
        data_start = res.data.find(b'<pre>') + 5
        data_end = res.data.find(b'</pre>', data_start)
        data = res.data[data_start:data_end]
        assert len(data) > 1


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_rest(api_app, users, video_metadata, project_published,
                      json_headers, smil_headers, es):
    """Test view."""
    indexer = RecordIndexer()
    (project, video_1, video_2) = project_published
    pid, record_project = project.fetch_published()
    vid, record_video = video_1.fetch_published()

    # index project
    project.indexer.index(record_project)
    # index a (update) video
    record_video['_files'] = video_metadata['_files']
    record_video.commit()
    db.session.commit()
    indexer.index(record_video)
    sleep(1)

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        url = url_for('invenio_records_rest.recid_item',
                      pid_value=pid.pid_value)
        url2 = url_for('invenio_records_rest.recid_item',
                       pid_value=vid.pid_value)

        # try get json
        res = client.get(url, headers=json_headers)
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict[
            'metadata']['_deposit']['id'] == project['_deposit']['id']

        # try get smil
        res = client.get(url, headers=smil_headers)
        assert res.status_code == 400

        res = client.get(url2, headers=smil_headers)
        assert res.status_code == 200

        root = ET.fromstring(res.data.decode('utf-8'))
        assert root.tag == 'smil'
        assert len(root[1][0]) == 4
        for child in root[1][0]:
            assert child.tag == 'video'
            assert child.attrib["system-bitrate"] == '11915822'
            assert child.attrib["width"] == '4096'
            assert child.attrib["height"] == '2160'

        src1 = video_metadata['_files'][0]['video'][0]['links']['self']
        src2 = video_metadata['_files'][0]['video'][1]['links']['self']
        src3 = video_metadata['_files'][0]['video'][2]['links']['self']
        src4 = video_metadata['_files'][0]['video'][3]['links']['self']

        assert root[1][0][0].attrib['src'] == src1
        assert root[1][0][1].attrib['src'] == src2
        assert root[1][0][2].attrib['src'] == src3
        assert root[1][0][3].attrib['src'] == src4
