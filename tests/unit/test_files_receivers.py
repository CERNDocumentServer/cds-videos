# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2018 CERN.
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

"""CDS files receivers tests."""

from __future__ import absolute_import

from mock import mock
from six import BytesIO

from invenio_db import db
from invenio_files_rest.models import Bucket, ObjectVersion, ObjectVersionTag

from cds.modules.files.receivers import on_download_rename_file

_MASTER_FILENAME_PREFIX = 'REPORT-NUMBER-002-001'
_MASTER_FILENAME = '{}.mov'.format(_MASTER_FILENAME_PREFIX)
_SUBTITLE_FILENAME = '{}_en.vtt'.format(_MASTER_FILENAME_PREFIX)
_SUBFORMAT1_FILENAME = '1080p.mp4'
_SUBFORMAT2_FILENAME = '720p.mp4'
_FRAME_FILENAME = 'frame-5.jpg'
_PLAYLIST_FILENAME = 'playlist.smil'
_EXTRA_FILENAME = 'extra.pdf'


def _fill_bucket_with_files(bucket):
    """Fill the given bucket with some files and tags."""
    # master, should not be renamed when downloaded
    master_obj = ObjectVersion.create(bucket=bucket,
                                      key=_MASTER_FILENAME,
                                      stream=BytesIO(b'content'))
    ObjectVersionTag.create(master_obj, 'context_type', 'master')

    # subformat 1
    subformat1_obj = ObjectVersion.create(bucket=bucket,
                                          key=_SUBFORMAT1_FILENAME,
                                          stream=BytesIO(b'content'))
    ObjectVersionTag.create(subformat1_obj, 'context_type', 'subformat')
    ObjectVersionTag.create(subformat1_obj, 'master', master_obj.version_id)
    # subformat 2
    subformat2_obj = ObjectVersion.create(bucket=bucket,
                                          key=_SUBFORMAT2_FILENAME,
                                          stream=BytesIO(b'content'))
    ObjectVersionTag.create(subformat2_obj, 'context_type', 'subformat')
    ObjectVersionTag.create(subformat2_obj, 'master', master_obj.version_id)
    # frame
    frame1_obj = ObjectVersion.create(bucket=bucket,
                                      key=_FRAME_FILENAME,
                                      stream=BytesIO(b'content'))
    ObjectVersionTag.create(frame1_obj, 'context_type', 'frame')
    ObjectVersionTag.create(frame1_obj, 'master', master_obj.version_id)
    # playlist
    playlist_obj = ObjectVersion.create(bucket=bucket,
                                        key=_PLAYLIST_FILENAME,
                                        stream=BytesIO(b'content'))
    ObjectVersionTag.create(playlist_obj, 'context_type', 'playlist')
    ObjectVersionTag.create(playlist_obj, 'master', master_obj.version_id)

    # subtitle, should not be renamed when downloaded
    subtitle_obj = ObjectVersion.create(bucket=bucket,
                                        key=_SUBTITLE_FILENAME,
                                        stream=BytesIO(b'content'))
    ObjectVersionTag.create(subtitle_obj, 'context_type', 'subtitle')

    # additional file, should not be renamed when downloaded
    additional_obj = ObjectVersion.create(bucket=bucket,
                                          key=_EXTRA_FILENAME,
                                          stream=BytesIO(b'content'))
    ObjectVersionTag.create(additional_obj, 'context_type', '')

    db.session.commit()


def test_download_filename_should_be_renamed(location):
    """Test files renamed when the file to download is a slave."""
    bucket = Bucket.create(location)
    _fill_bucket_with_files(bucket)

    obj = ObjectVersion.get(bucket, _SUBFORMAT1_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == '{}-{}'.format(_MASTER_FILENAME_PREFIX,
                                     _SUBFORMAT1_FILENAME)

    obj = ObjectVersion.get(bucket, _SUBFORMAT2_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == '{}-{}'.format(_MASTER_FILENAME_PREFIX,
                                     _SUBFORMAT2_FILENAME)

    obj = ObjectVersion.get(bucket, _FRAME_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == '{}-{}'.format(_MASTER_FILENAME_PREFIX,
                                     _FRAME_FILENAME)

    obj = ObjectVersion.get(bucket, _PLAYLIST_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == '{}-{}'.format(_MASTER_FILENAME_PREFIX,
                                     _PLAYLIST_FILENAME)


def test_download_filename_should_not_be_renamed(location):
    """Test files not renamed when the file to download is not a slave."""
    bucket = Bucket.create(location)
    _fill_bucket_with_files(bucket)

    obj = ObjectVersion.get(bucket, _MASTER_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == _MASTER_FILENAME

    obj = ObjectVersion.get(bucket, _SUBTITLE_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == _SUBTITLE_FILENAME

    obj = ObjectVersion.get(bucket, _EXTRA_FILENAME)
    on_download_rename_file(None, obj)
    assert obj.key == _EXTRA_FILENAME


def test_response_headers(api_app, location):
    """Test http response headers when downloading files."""
    bucket = Bucket.create(location)
    _fill_bucket_with_files(bucket)

    _URL = '/files/{bucket_id}/{key}?download'

    # ignore permissions and test http response headers
    with mock.patch('invenio_files_rest.views.check_permission'), \
            api_app.test_client() as client:
        # no renaming
        res = client.get(_URL.format(bucket_id=bucket.id,
                                     key=_MASTER_FILENAME))
        assert res.status_code == 200
        expected = 'attachment; filename={}'.format(_MASTER_FILENAME)
        assert res.headers['Content-Disposition'] == expected

        # file renamed
        res = client.get(_URL.format(bucket_id=bucket.id,
                                     key=_SUBFORMAT1_FILENAME))
        assert res.status_code == 200
        expected = 'attachment; filename={}-{}'.format(_MASTER_FILENAME_PREFIX,
                                                       _SUBFORMAT1_FILENAME)
        assert res.headers['Content-Disposition'] == expected
