# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""CDS Webhooks tests for Celery tasks."""

from __future__ import absolute_import

import mock
import uuid
import shutil
import tempfile

from os import listdir
from os.path import getsize, isfile, join
from random import randint


from cds.modules.webhooks.tasks import attach_files, download, \
    extract_frames, transcode


def download_with_size(url, bucket_id, chunk_size, task_id, size, key=None):
    """Download mock file with given size."""
    content = b'\x00' * size
    with mock.patch('requests.get') as mock_http:
        mock_http.return_value = type('Response', (object,), {
            'headers': {'Content-Length': size},
            'content': content,
            'iter_content': lambda _, **kw: (
                content[pos:pos + kw['chunk_size']]
                for pos in range(0, len(content), kw['chunk_size'])
            )
        })()
        f = download.delay(url, bucket_id, chunk_size, task_id, key).result
    assert getsize(f) == size


def test_download(bucket):
    """Test download task."""
    args = ['http://example.com/video.mp4', bucket.id, 6000000, 'id']
    download_with_size(*args, size=10)
    download_with_size(*args, size=10000000)


def test_download_and_rename(bucket):
    """Test renaming during the downloading."""
    args = ['http://example.com/video.mp4', bucket.id, 6000000, 'id']
    download_with_size(*args, size=10000000, key='new_name')


def test_sorenson(app):
    """Test transcode task."""
    with mock.patch(
            'cds.modules.webhooks.tasks.start_encoding'
    ) as mock_start, mock.patch(
        'cds.modules.webhooks.tasks.get_encoding_status'
    ) as mock_get, mock.patch(
        'cds.modules.webhooks.tasks.stop_encoding'
    ) as mock_stop:

        # Mock Sorenson responses
        mock_start.return_value = uuid.uuid4()
        mock_get.side_effect = [
            dict(Status=dict(Progress=0, TimeFinished=None)),
            dict(Status=dict(Progress=45, TimeFinished=None)),
            dict(Status=dict(Progress=95, TimeFinished=None)),
            dict(Status=dict(Progress=100, TimeFinished='12:00')),
        ]
        mock_stop.return_value = None

        with app.app_context():
            assert transcode('video_filename', 'Youtube 480p', 'id') == \
                app.config['CDS_SORENSON_OUTPUT_FOLDER']


def test_frame_extraction(video_mp4, location):
    """Test extract_frames task."""
    tmp = location.uri
    extract_frames(
        input_filename=video_mp4,
        start_percentage=5,
        end_percentage=95,
        number_of_frames=10,
        size_percentage=10,
        output_folder=tmp,
        parent_id='test'
    )
    assert len([f for f in listdir(tmp) if isfile(join(tmp, f))]) == 10


def test_file_attachment(bucket):
    """Test attach_files task."""
    assert bucket.size == 0

    # Setup
    folder_no = randint(1, 10)
    folders = [tempfile.mkdtemp() for _ in range(folder_no)]

    # Create files
    total_size = 0
    for tmp in folders:
        file_no = randint(1, 10)
        file_size = randint(100, 1000)
        for i in range(file_no):
            tmp_file = open(join(tmp, '{}.txt'.format(i)), 'w')
            tmp_file.write('$' * file_size)
            tmp_file.close()
        total_size += file_no * file_size

    # Attach to bucket
    attach_files(folders, bucket.id, 'key', 'id')

    assert bucket.size == total_size

    # Cleanup
    map(shutil.rmtree, folders)
