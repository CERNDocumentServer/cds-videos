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

"""Test previewer."""

from __future__ import absolute_import, print_function

import pytest
from cds.modules.previewer.api import get_relative_path

from flask import url_for
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.models import RecordsBuckets
from helpers import prepare_videos_for_publish

from werkzeug.exceptions import NotFound

from invenio_files_rest.models import ObjectVersion, ObjectVersionTag

from werkzeug.utils import import_string
from helpers import new_project


@pytest.mark.parametrize(
    'preview_func, publish, endpoint_template, ui_blueprint', [
        ('preview_recid', True, '/record/{0}/preview/{1}', 'recid_preview'),
        ('preview_recid_embed', True, '/record/{0}/embed/{1}', 'recid_embed'),
        ('preview_depid', False, '/deposit/{0}/preview/video/{1}',
         'video_preview'),
    ])
def test_preview_video(previewer_app, es, db, cds_jsonresolver, users,
                       location, deposit_metadata, video, preview_func,
                       publish, endpoint_template, ui_blueprint):
    """Test record video previewing."""
    project = new_project(previewer_app, es, cds_jsonresolver, users,
                          location, db, deposit_metadata)

    project, video_1, _ = project
    basename = 'test'
    filename_1 = '{}.mp4'.format(basename)
    filename_2 = '{}.invalid'.format(basename)
    deposit_filename = 'playlist.m3u8'
    bucket_id = video_1['_buckets']['deposit']
    preview_func = import_string(
        'cds.modules.previewer.views.{0}'.format(preview_func))

    # Create objects
    obj = ObjectVersion.create(bucket=bucket_id, key=filename_1,
                               stream=open(video, 'rb'))
    ObjectVersionTag.create(obj, 'context_type', 'master')
    ObjectVersionTag.create(obj, 'preview', True)
    ObjectVersion.create(bucket=bucket_id, key=filename_2,
                         stream=open(video, 'rb'))

    success_list = ['theoplayer.onReady', 'playbackRates']

    if publish:
        prepare_videos_for_publish([video_1])
        video_1 = video_1.publish()
        assert video_1.status == 'published'
        pid, video_1 = video_1.fetch_published()

        # Get SMIL url
        new_bucket = RecordsBuckets.query.filter_by(
            record_id=video_1.id).one().bucket_id
        smil_obj = ObjectVersion.get(new_bucket, '{}.smil'.format(basename))
        assert smil_obj

        wowza_url = previewer_app.config['WOWZA_PLAYLIST_URL'].format(
            filepath=get_relative_path(smil_obj))
        success_list.append(wowza_url)
    else:
        assert video_1.status == 'draft'
        pid = PersistentIdentifier.get('depid', video_1['_deposit']['id'])
        success_list.append(deposit_filename)

    def assert_preview(expected=None, exception=None, **query_params):
        with previewer_app.test_request_context(query_string=query_params):
            if exception is not None:
                with pytest.raises(exception):
                    preview_func(pid, video_1)
            else:
                if 'filename' in query_params:
                    filename = query_params['filename']
                    try:
                        pid_value = pid.pid_value
                    except AttributeError:
                        pid_value = pid
                    assert url_for(
                        'invenio_records_ui.{0}'.format(ui_blueprint),
                        pid_value=pid_value,
                        filename=filename,
                    ) == endpoint_template.format(pid_value, filename)
                for exp in expected:
                    assert exp in preview_func(pid, video_1)

    # Non-existent filename
    assert_preview(exception=NotFound, filename='non-existent')
    # Invalid extension
    assert_preview(expected=['Cannot preview file'], filename=filename_2)
    # Specific filename
    assert_preview(expected=success_list, filename=filename_1)
    # No filename (falls back to file with preview tag)
    assert_preview(expected=success_list)


@pytest.mark.parametrize(
    'preview_func, publish, endpoint_template, ui_blueprint', [
        ('preview_recid', True, '/record/{0}/preview/{1}', 'recid_preview'),
        ('preview_recid_embed', True, '/record/{0}/embed/{1}', 'recid_embed'),
        ('preview_depid', False, '/deposit/{0}/preview/video/{1}',
         'video_preview'),
    ])
def test_preview_video_html5(previewer_app, es, db, cds_jsonresolver, users,
                             location, deposit_metadata, video, preview_func,
                             publish, endpoint_template, ui_blueprint):
    """Test record video previewing."""
    # Enable HTML5 player
    previewer_app.config['THEO_LICENCE_KEY'] = None
    project = new_project(previewer_app, es, cds_jsonresolver, users,
                          location, db, deposit_metadata)

    project, video_1, _ = project
    basename = 'test'
    filename_1 = '{}.mp4'.format(basename)
    filename_2 = '{}.invalid'.format(basename)
    deposit_filename = 'playlist.m3u8'
    bucket_id = video_1['_buckets']['deposit']
    preview_func = import_string(
        'cds.modules.previewer.views.{0}'.format(preview_func))

    # Create objects
    obj = ObjectVersion.create(bucket=bucket_id, key=filename_1,
                               stream=open(video, 'rb'))
    ObjectVersionTag.create(obj, 'context_type', 'master')
    ObjectVersionTag.create(obj, 'preview', True)
    ObjectVersion.create(bucket=bucket_id, key=filename_2,
                         stream=open(video, 'rb'))

    success_list = [
        '<video',
    ]

    if publish:
        prepare_videos_for_publish([video_1])
        video_1 = video_1.publish()
        assert video_1.status == 'published'
        pid, video_1 = video_1.fetch_published()
    else:
        assert video_1.status == 'draft'
        pid = PersistentIdentifier.get('depid', video_1['_deposit']['id'])

    def assert_preview(expected=None, exception=None, **query_params):
        with previewer_app.test_request_context(query_string=query_params):
            if exception is not None:
                with pytest.raises(exception):
                    preview_func(pid, video_1)
            else:
                if 'filename' in query_params:
                    filename = query_params['filename']
                    try:
                        pid_value = pid.pid_value
                    except AttributeError:
                        pid_value = pid
                    assert url_for(
                        'invenio_records_ui.{0}'.format(ui_blueprint),
                        pid_value=pid_value,
                        filename=filename,
                    ) == endpoint_template.format(pid_value, filename)
                for exp in expected:
                    assert exp in preview_func(pid, video_1)

    # Non-existent filename
    assert_preview(exception=NotFound, filename='non-existent')
    # Invalid extension
    assert_preview(expected=['Cannot preview file'], filename=filename_2)
    # Specific filename
    assert_preview(expected=success_list, filename=filename_1)
    # No filename (falls back to file with preview tag)
    assert_preview(expected=success_list)


def test_legacy_embed(previewer_app, db, api_project, video):
    """Test backwards-compatibility with legacy embed URL for videos."""
    project, video_1, _ = api_project
    filename = 'test.mp4'
    bucket_id = video_1['_buckets']['deposit']
    obj = ObjectVersion.create(bucket=bucket_id, key=filename,
                               stream=open(video, 'rb'))
    ObjectVersionTag.create(obj, 'context_type', 'master')
    ObjectVersionTag.create(obj, 'preview', True)
    prepare_videos_for_publish([video_1])
    video_1 = video_1.publish()

    with previewer_app.test_client() as client:
        res = client.get('/video/{0}'.format(video_1.report_number))
        assert res.location.endswith(url_for(
            'invenio_records_ui.recid_embed_default',
            pid_value=video_1['recid'],
        ))


def test_smil_generation(previewer_app, db, api_project, video):
    """Test SMIL file export from video."""
    def create_slave(key):
        """Create a slave."""
        slave = ObjectVersion.create(bucket=bucket_id,
                                     key=key, stream=open(video, 'rb'))
        ObjectVersionTag.create(slave, 'master', str(master_obj.version_id))
        return slave

    def create_video_tags(obj, context_type, bitrate=None):
        """Create video tags."""
        tags = [('width', 1000), ('height', 1000),
                ('bit_rate', 123456), ('video_bitrate', bitrate or 123456),
                ('media_type', 'video'), ('context_type', context_type)]
        [ObjectVersionTag.create(obj, key, val) for key, val in tags]

    project, video_1, _ = api_project
    basename = 'test'
    bucket_id = video_1['_buckets']['deposit']
    master_obj = ObjectVersion.create(bucket=bucket_id,
                                      key='{}.mp4'.format(basename),
                                      stream=open(video, 'rb'))
    ObjectVersionTag.create(master_obj, 'preview', True)
    create_video_tags(master_obj, context_type='master')
    for i in range(4):
        slave = create_slave(key='{0}_{1}.mp4'.format(basename, i))
        create_video_tags(slave, context_type='subformat')

    # Create one slave that shouldn't be added to the SMIL file
    no_smil_slave = create_slave(key='test_no_smil.mp4')
    create_video_tags(no_smil_slave, context_type='subformat', bitrate=9876)
    ObjectVersionTag.create(no_smil_slave, 'smil', False)
    # and one that should be added to the SMIL file
    yes_smil_slave = create_slave(key='test_no_smil.mp4')
    create_video_tags(yes_smil_slave, context_type='subformat', bitrate=7654)
    ObjectVersionTag.create(yes_smil_slave, 'smil', True)

    # publish video
    prepare_videos_for_publish([video_1])
    video_1.publish()
    _, video_record = video_1.fetch_published()
    new_bucket = RecordsBuckets.query.filter_by(
        record_id=video_record.id).one().bucket_id

    # Check that SMIL file has been properly generated
    smil_obj = ObjectVersion.get(new_bucket, '{}.smil'.format(basename))
    assert smil_obj
    assert ObjectVersionTag.query.filter_by(
        object_version=smil_obj, key='context_type', value='playlist'
    ).one_or_none()

    # Check SMIL contents
    with open(smil_obj.file.uri, 'r') as smil_file:
        contents = smil_file.read()
        for suffix in range(4):
            slave_key = '{0}_{1}.mp4'.format(basename, suffix)
            slave_obj = ObjectVersion.get(new_bucket, slave_key)
            assert get_relative_path(slave_obj) in contents

        # check if special file is out of the smile
        assert 'system-bitrate="9876"' not in contents
        # check if special file is inside the smile
        assert 'system-bitrate="7654"' in contents


def test_vtt_export(previewer_app, db, project_published,
                    video_record_metadata):
    """Test VTT export endpoint."""
    (project, video_1, video_2) = project_published
    # index a (update) video
    _, record_video = video_1.fetch_published()
    record_video.update(**video_record_metadata)
    record_video.commit()
    db.session.commit()
    vid = video_1['_deposit']['pid']['value']
    with previewer_app.test_request_context():
        vtt_url = url_for(
            'invenio_records_ui.recid_export', pid_value=vid, format='vtt')
    with previewer_app.test_client() as client:
        res = client.get(vtt_url)
        assert res.status_code == 200
        data = res.data.decode('utf-8')
        assert 'WEBVTT' in data
        for i in range(1, 11):
            assert 'frame-{0}.jpg'.format(i) in data
