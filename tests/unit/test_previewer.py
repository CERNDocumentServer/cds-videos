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

from werkzeug.exceptions import NotFound

from invenio_files_rest.models import ObjectVersion, ObjectVersionTag

from cds.modules.records.providers import CDSRecordIdProvider
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
    if publish:
        video_1 = video_1.publish()
        assert video_1.status == 'published'
        pid = CDSRecordIdProvider.get(video_1['recid']).pid
    else:
        assert video_1.status == 'draft'
        pid = video_1['_deposit']['id']

    filename_1 = 'test.mp4'
    filename_2 = 'test.invalid'
    bucket_id = video_1['_buckets']['deposit']
    preview_func = import_string(
        'cds.modules.previewer.views.{0}'.format(preview_func))

    # Create objects
    obj = ObjectVersion.create(bucket=bucket_id, key=filename_1,
                               stream=open(video, 'rb'))
    ObjectVersion.create(bucket=bucket_id, key=filename_2,
                         stream=open(video, 'rb'))

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

    # Non-existent filename
    assert_preview(exception=NotFound, filename='non-existent')
    # Neither filename nor preview tag: 404
    assert_preview(exception=NotFound)
    # Invalid extension
    assert_preview(expected='Cannot preview file', filename=filename_2)
    # Only filename
    assert_preview(expected=filename_1, filename=filename_1)
    # Only preview tag
    ObjectVersionTag.create(obj, 'preview', True)
    assert_preview(expected=filename_1)
