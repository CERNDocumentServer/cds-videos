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

from flask import url_for
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.models import RecordsBuckets
from helpers import prepare_videos_for_publish

from werkzeug.exceptions import NotFound

from invenio_files_rest.models import ObjectVersion, ObjectVersionTag

from werkzeug.utils import import_string


@pytest.mark.parametrize(
    'preview_func, publish, endpoint_template, ui_blueprint', [
        ('preview_recid', True, '/record/{0}/preview/{1}', 'recid_preview'),
        ('preview_recid_embed', True, '/record/{0}/embed/{1}', 'recid_embed'),
        ('preview_depid', False, '/deposit/{0}/preview/video/{1}',
         'video_preview'),
    ])
def test_preview_video(previewer_app, db, project, video, preview_func,
                       publish, endpoint_template, ui_blueprint):
    """Test record video previewing."""
    project, video_1, _ = project
    filename_1 = 'test.mp4'
    filename_2 = 'test.invalid'
    bucket_id = video_1['_buckets']['deposit']
    preview_func = import_string(
        'cds.modules.previewer.views.{0}'.format(preview_func))

    # Create objects
    obj = ObjectVersion.create(bucket=bucket_id, key=filename_1,
                               stream=open(video, 'rb'))
    ObjectVersionTag.create(obj, 'preview', True)
    ObjectVersion.create(bucket=bucket_id, key=filename_2,
                         stream=open(video, 'rb'))

    if publish:
        prepare_videos_for_publish(video_1)
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

                assert expected in preview_func(pid, video_1)

    success_string = 'theoplayer.onReady'
    # Non-existent filename
    assert_preview(exception=NotFound, filename='non-existent')
    # Invalid extension
    assert_preview(expected='Cannot preview file', filename=filename_2)
    # Specific filename
    assert_preview(expected=success_string, filename=filename_1)
    # No filename (falls back to file with preview tag)
    assert_preview(expected=success_string)


def test_legacy_embed(previewer_app, db, project, video):
    """Test backwards-compatibility with legacy embed URL for videos."""
    project, video_1, _ = project
    filename = 'test.mp4'
    bucket_id = video_1['_buckets']['deposit']
    obj = ObjectVersion.create(bucket=bucket_id, key=filename,
                               stream=open(video, 'rb'))
    ObjectVersionTag.create(obj, 'preview', True)
    prepare_videos_for_publish(video_1)
    video_1 = video_1.publish()

    with previewer_app.test_client() as client:
        res = client.get('/video/{0}'.format(video_1.report_number))
        assert res.location.endswith(url_for(
            'invenio_records_ui.recid_embed',
            pid_value=video_1['recid'],
            filename='',
        ))


def test_smil_generation(previewer_app, db, project, video):
    """Test SMIL file export from video."""

    def create_video_tags(obj, context_type):
        """Create video tags."""
        tags = [('width', 10), ('height', 10), ('bit_rate', 10),
                ('media_type', 'video'), ('context_type', context_type)]
        [ObjectVersionTag.create(obj, key, val) for key, val in tags]

    project, video_1, _ = project
    basename = 'test'
    bucket_id = video_1['_buckets']['deposit']
    master_obj = ObjectVersion.create(bucket=bucket_id,
                                      key='{}.mp4'.format(basename),
                                      stream=open(video, 'rb'))
    ObjectVersionTag.create(master_obj, 'preview', True)
    create_video_tags(master_obj, context_type='master')
    for i in range(4):
        slave = ObjectVersion.create(bucket=bucket_id,
                                     key='{0}_{1}.mp4'.format(basename, i),
                                     stream=open(video, 'rb'))
        ObjectVersionTag.create(slave, 'master', str(master_obj.version_id))
        create_video_tags(slave, context_type='subformat')

    prepare_videos_for_publish(video_1)
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
            assert '{0}_{1}.mp4'.format(basename, suffix) in contents


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
