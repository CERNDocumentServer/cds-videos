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

"""CDS tests for Webhook Celery tasks."""

from __future__ import absolute_import

import mock
import uuid
import shutil
import tempfile

from os import listdir
from random import randint

from cds.modules.webhooks.receivers import AVCWorkflow
from celery import states
import os

from cds.modules.webhooks.tasks import attach_files, download, \
    extract_frames, transcode, chain_orchestrator
from os.path import isfile, join

from celery.result import AsyncResult
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record


def download_with_size(url, bucket_id, chunk_size,
                       size, key=None, parent=None):
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
        kwargs = dict(parent=parent, key=key)
        f = download.delay(url, bucket_id, chunk_size, **kwargs).result
    assert os.path.getsize(f) == size


def test_download(bucket):
    """Test download task."""
    args = ['http://example.com/video.mp4', bucket.id, 6000000]
    download_with_size(*args, size=10)
    download_with_size(*args, size=10000000)


def test_download_and_rename(bucket):
    """Test renaming during the downloading."""
    args = ['http://example.com/video.mp4', bucket.id, 6000000]
    download_with_size(*args, size=10000000, key='new_name')


def test_sorenson(app, mock_sorenson):
    """Test transcode task."""
    with app.app_context():
        assert transcode.delay(
            'video_filename', 'Youtube 480p'
        ).result == app.config['CDS_SORENSON_OUTPUT_FOLDER']


def test_frame_extraction(video_mp4, location):
    """Test extract_frames task."""
    tmp = location.uri

    # Extract frames from video
    extract_frames.delay(
        input_filename=video_mp4,
        start_percentage=5,
        end_percentage=95,
        number_of_frames=10,
        size_percentage=10,
        output_folder=tmp
    )

    # Check all frame thumbnails were extracted
    assert len([f for f in listdir(tmp) if isfile(join(tmp, f))]) == 10


def test_file_attachment(db, bucket):
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
    attach_files.delay(folders, bucket.id)

    # Check bucket is properly populated
    db.session.add(bucket)
    assert bucket.size == total_size

    # Cleanup
    map(shutil.rmtree, folders)


def test_orchestrator(bucket, location, depid, mock_sorenson):
    """Test orchestrator task."""

    # Generate master ID
    task_id = str(uuid.uuid4())

    # Define task workflow
    workflow = AVCWorkflow.workflow

    # Start orchestration
    chain_orchestrator.apply_async(
        (workflow, ),
        kwargs=dict(
            dep_id=depid,
            url='http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4',
            bucket_id=bucket.id,
            chunk_size=5242880,
            preset_name='Youtube 480p',
            start_percentage=5,
            end_percentage=95,
            number_of_frames=10,
            size_percentage=5,
            output_folder=location.uri
        ),
        task_id=task_id)

    # Check progress report on Celery backend
    result = AsyncResult(task_id)
    (state, meta) = result.state, result.info or {}

    assert state == states.STARTED
    for task in ['download', 'transcode', 'extract_frames', 'attach_files']:
        assert task in meta
        assert 'order' in meta[task]
        assert 'percentage' in meta[task]
        assert meta[task]['percentage'] == 100

    # Check progress report on deposit
    recid = PersistentIdentifier.get('depid', depid).object_uuid
    record = Record.get_record(recid)

    assert 'process' in record['_deposit']
    state = record['_deposit']['process']

    assert state == dict(
        task_id=task_id,
        download={'order': 1, 'status': 'DONE'},
        transcode={'order': 2, 'status': 'DONE'},
        extract_frames={'order': 2, 'status': 'DONE'},
        attach_files={'order': 3, 'status': 'DONE'},
    )
