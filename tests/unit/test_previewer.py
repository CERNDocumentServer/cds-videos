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

from invenio_files_rest.models import ObjectVersion

from cds.modules.previewer.views import preview_depid


def test_previewer_on_deposit(previewer_app, db, project, video):
    """Test video previewer on deposit."""
    (project, video_1, video_2) = project

    deposit_video_schema = ('https://cdslabs.cern.ch/schemas/'
                            'deposits/records/video-v1.0.0.json')

    # check video1 is not published
    assert video_1['_deposit']['status'] == 'draft'
    # and the schema is a deposit
    assert video_1['$schema'] == deposit_video_schema

    filename_1 = 'jessica_jones.mp4'
    filename_2 = 'jessica_jones.harley_quinn'

    bucket_id = video_1['_buckets']['deposit']
    ObjectVersion.create(bucket=bucket_id, key=filename_1,
                         stream=open(video, 'rb'))
    ObjectVersion.create(bucket=bucket_id, key=filename_2,
                         stream=open(video, 'rb'))
    db.session.commit()

    expected_url_1 = '/deposit/{0}/preview/video/{1}'.format(
        video_1['_deposit']['id'],
        filename_1
    )

    expected_url_2 = '/deposit/{0}/preview/video/{1}'.format(
        video_1['_deposit']['id'],
        filename_2
    )

    _url = '/?filename={0}'.format(filename_1)
    with previewer_app.test_request_context(_url):
        url = url_for(
            'invenio_records_ui.video_preview',
            pid_value=video_1['_deposit']['id'], filename=filename_1
        )
        assert url == expected_url_1

        preview = preview_depid(video_1.pid, video_1)

    assert filename_1 in preview

    _url = '/?filename={0}'.format(filename_2)
    with previewer_app.test_request_context(_url):
        url = url_for(
            'invenio_records_ui.video_preview',
            pid_value=video_1['_deposit']['id'], filename=filename_2
        )
        assert url == expected_url_2

        preview = preview_depid(video_1.pid, video_1)

        assert 'Cannot preview file' in preview

    _url = '/?filename={0}'.format('Doctor Strange')
    with previewer_app.test_request_context(_url):
        with pytest.raises(NotFound):
            preview_depid(video_1.pid, video_1)
