# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017 CERN.
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

"""Test records."""

from __future__ import absolute_import, print_function

from functools import partial

import mock
import json

import re
from invenio_indexer.api import RecordIndexer
from invenio_db import db
from time import sleep
from flask import url_for
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session

from helpers import get_files_metadata, assert_hits_len


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_ui_export(app, project_published, video_record_metadata):
    """Test view."""
    (project, video_1, video_2) = project_published
    # index a (update) video
    _, record_video = video_1.fetch_published()
    record_video.update(**video_record_metadata)
    record_video.commit()
    db.session.commit()
    pid = project['_deposit']['pid']['value']
    vid = video_1['_deposit']['pid']['value']
    url_no_existing_exporter = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=pid, format='blabla')
    url_not_valid_type_record = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=pid, format='smil')
    url_valid_smil = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=vid, format='smil')
    url_valid_vtt = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=vid, format='vtt')
    url_valid_json = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=pid, format='json')
    url_valid_drupal = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=vid, format='drupal')
    url_valid_drupal_project = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=pid, format='drupal')
    url_valid_datacite_video = partial(
        url_for, 'invenio_records_ui.recid_export',
        pid_value=vid, format='dcite')

    def get_pre(data):
        data = data.decode('utf-8')
        data_start = data.find('<pre>') + 5
        data_end = data.find('</pre>', data_start)
        return data[data_start:data_end]

    def check_url(partial_url, status_code):
        res = client.get(partial_url())
        res_raw = client.get(partial_url(raw=True))
        assert res.status_code == status_code
        assert res_raw.status_code == status_code
        return res.data

    with app.test_request_context():
        with app.test_client() as client:
            check_url(url_no_existing_exporter, 404)
            check_url(url_not_valid_type_record, 400)

            data = check_url(url_valid_smil, 200)
            assert get_pre(data).startswith('&lt;smil&gt;')

            data = check_url(url_valid_vtt, 200)
            assert 'WEBVTT' in data.decode('utf-8')

            check_url(url_valid_json, 200)

            data = check_url(url_valid_drupal, 200)
            assert get_pre(data).startswith('{')

            data = check_url(url_valid_drupal_project, 200)
            assert get_pre(data) == '{}'

            data = check_url(url_valid_datacite_video, 200)
            assert get_pre(data).startswith('&lt;?xml version=')


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_rest(api_app, users, es, api_project_published, vtt_headers,
                      datacite_headers, json_headers, smil_headers,
                      drupal_headers, extra_metadata, _deposit_metadata):
    """Test view."""
    indexer = RecordIndexer()
    (project, video_1, video_2) = api_project_published
    pid, record_project = project.fetch_published()
    vid, record_video = video_1.fetch_published()
    bucket_id = str(video_1['_buckets']['deposit'])

    # index project
    project.indexer.index(record_project)
    # index video
    record_video['_files'] = get_files_metadata(bucket_id)
    record_video['_deposit'].update(_deposit_metadata)
    record_video.update(extra_metadata)
    record_video.commit()
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
        assert res.status_code == 200
        project_dict = json.loads(res.data.decode('utf-8'))
        assert project_dict[
            'metadata']['_deposit']['id'] == project['_deposit']['id']

        # try get smil
        res = client.get(url, headers=smil_headers)
        assert res.status_code == 400

        res = client.get(url2, headers=smil_headers)
        assert res.status_code == 200

        # try get vtt
        res = client.get(url, headers=vtt_headers)
        assert res.status_code == 400

        res = client.get(url2, headers=vtt_headers)
        assert res.status_code == 200

        # try get drupal
        file_frame = 'http://cds.cern.ch/api/files/123/frame-1.jpg'
        with mock.patch('cds.modules.records.api.CDSFileObject._link',
                        return_value=file_frame):
            res = client.get(url2, headers=drupal_headers)

        assert res.status_code == 200
        drupal = json.loads(res.data.decode('utf-8'))
        thumbnail = u'http://cds.cern.ch/api/files/123/frame-1.jpg'
        expected = {
            u'entries': [
                {
                    u'entry': {
                        u'caption_en': u'in tempor reprehenderit enim eiusmod',
                        u'caption_fr': u'france caption',
                        u'copyright_date': u'2017',
                        u'copyright_holder': u'CERN',
                        u'creation_date': u'2017-03-02',
                        u'directors': u'paperone, pluto',
                        u'entry_date': u'2016-12-03',
                        u'id': u'CERN-MOVIE-2016-1-1',
                        u'keywords': u'keyword1, keyword2',
                        u'license_body': u'GPLv2',
                        u'license_url': u'http://license.cern.ch',
                        u'producer': u'nonna papera, zio paperino',
                        u'record_id': u'1',
                        u'thumbnail': thumbnail,
                        u'title_en': u'My english title',
                        u'title_fr': u'My french title',
                        u'type': u'video',
                        u'video_length': u'00:01:00.140',
                    }
                }
            ]
        }
        assert expected == drupal

        # try get datacite
        res = client.get(url2, headers=datacite_headers)
        assert res.status_code == 200
        assert res.data.decode('utf-8').startswith('<?xml version=')

    # test corner cases
    del record_video['title_translations']
    del record_video['description_translations']
    record_video.commit()
    db.session.commit()

    with api_app.test_client() as client:
        # try get drupal
        file_frame = 'http://cds.cern.ch/api/files/123/frame-1.jpg'
        with mock.patch('cds.modules.records.api.CDSFileObject._link',
                        return_value=file_frame):
            res = client.get(url2, headers=drupal_headers)

        assert res.status_code == 200
        drupal = json.loads(res.data.decode('utf-8'))
        thumbnail = u'http://cds.cern.ch/api/files/123/frame-1.jpg'
        expected = {
            u'entries': [
                {
                    u'entry': {
                        u'caption_en': u'in tempor reprehenderit enim eiusmod',
                        u'caption_fr': u'',
                        u'copyright_date': u'2017',
                        u'copyright_holder': u'CERN',
                        u'creation_date': u'2017-03-02',
                        u'directors': u'paperone, pluto',
                        u'entry_date': u'2016-12-03',
                        u'id': u'CERN-MOVIE-2016-1-1',
                        u'keywords': u'keyword1, keyword2',
                        u'license_body': u'GPLv2',
                        u'license_url': u'http://license.cern.ch',
                        u'producer': u'nonna papera, zio paperino',
                        u'record_id': u'1',
                        u'thumbnail': thumbnail,
                        u'title_en': u'My english title',
                        u'title_fr': u'',
                        u'type': u'video',
                        u'video_length': u'00:01:00.140',
                    }
                }
            ]
        }
        assert expected == drupal


def test_video_duration(app, video_published):
    """Validate calculated duration of video."""
    assert re.match(r'^\d\d:\d\d:\d\d.\d\d\d$', video_published['duration'])


def test_videos_search(api_app, indexed_videos):
    """Test that searching for videos returns correct number of results."""
    with api_app.test_client() as client:
        search_url = url_for('invenio_records_rest.recid_list')
        # Get a query with only one record
        res = client.get(search_url, query_string={'q': 'video'})
        assert_hits_len(res, 3)
        assert res.status_code == 200

        # Also make sure that there is no "Project" in the results
        res = client.get(search_url, query_string={'q': 'Project'})
        assert_hits_len(res, 0)
        assert res.status_code == 200
