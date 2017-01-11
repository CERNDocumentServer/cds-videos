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

import threading
import time
import mock
import pytest

from invenio_files_rest.models import ObjectVersion, ObjectVersionTag, \
    Bucket, FileInstance
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_records.models import RecordMetadata
from six import BytesIO, next
from celery.exceptions import Retry
from sqlalchemy.orm.exc import ConcurrentModificationError

from cds.modules.webhooks.tasks import (DownloadTask,
                                        update_record, ExtractFramesTask,
                                        ExtractMetadataTask,
                                        TranscodeVideoTask)

from helpers import transcode_task


def test_download_to_object_version(db, bucket):
    """Test download to object version task."""
    with mock.patch('requests.get') as mock_request:
        obj = ObjectVersion.create(bucket=bucket, key='test.pdf')
        bid = bucket.id
        db.session.commit()

        # Mock download request
        file_size = 1024
        mock_request.return_value = type(
            'Response', (object, ), {
                'raw': BytesIO(b'\x00' * file_size),
                'headers': {'Content-Length': file_size}
            })
        assert obj.file is None

        task_s = DownloadTask().s('http://example.com/test.pdf',
                                  version_id=obj.version_id)
        # Download
        task = task_s.delay()
        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        assert obj.key == 'test.pdf'
        assert str(obj.version_id) == task.result
        assert obj.file
        assert obj.file.size == file_size
        assert Bucket.get(bid).size == file_size
        assert FileInstance.query.count() == 1

        # Undo
        DownloadTask().clean(version_id=obj.version_id)

        assert ObjectVersion.query.count() == 0
        assert FileInstance.query.count() == 0
        assert Bucket.get(bid).size == 0


def test_update_record_thread(app, db):
    """Test update record with multiple concurrent transactions."""
    if db.engine.name == 'sqlite':
        raise pytest.skip(
            'Concurrent transactions are not supported nicely on SQLite')

    # Create record
    recid = str(Record.create({}).id)
    db.session.commit()

    class RecordUpdater(threading.Thread):
        def __init__(self, path, value):
            super(RecordUpdater, self).__init__()
            self.path = path
            self.value = value

        def run(self):
            with app.app_context():
                update_record.delay(recid, [{
                    'op': 'add',
                    'path': '/{}'.format(self.path),
                    'value': self.value,
                }])

    # Run threads
    thread1 = RecordUpdater('test1', 1)
    thread2 = RecordUpdater('test2', 2)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Check that record was patched properly
    record = Record.get_record(recid)
    assert record.dumps() == {'test1': 1, 'test2': 2}


def test_update_record_retry(app, db):
    """Test update record with retry."""
    # Create record
    recid = str(Record.create({}).id)
    patch = [{
        'op': 'add',
        'path': '/fuu',
        'value': 'bar',
    }]
    db.session.commit()
    with mock.patch(
            'invenio_records.api.Record.validate',
            side_effect=[ConcurrentModificationError, None]) as mock_commit:
        with pytest.raises(Retry):
            update_record.s(recid=recid, patch=patch).apply()
        assert mock_commit.call_count == 2

    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert records[0].json == {'fuu': 'bar'}


def test_metadata_extraction_video_mp4(app, db, cds_depid, bucket, video_mp4):
    """Test metadata extraction video mp4."""
    # Extract metadata
    obj = ObjectVersion.create(bucket=bucket, key='video.mp4')
    obj_id = str(obj.version_id)
    dep_id = str(cds_depid)
    task_s = ExtractMetadataTask().s(uri=video_mp4,
                                     version_id=obj_id,
                                     deposit_id=dep_id)

    # Extract metadata
    task_s.delay()

    # Check that deposit's metadata got updated
    recid = PersistentIdentifier.get('depid', cds_depid).object_uuid
    record = Record.get_record(recid)
    assert 'extracted_metadata' in record['_deposit']
    assert record['_deposit']['extracted_metadata']

    # Check that ObjectVersionTags were added
    tags = ObjectVersion.query.first().get_tags()
    assert tags['duration'] == '60.095000'
    assert tags['bit_rate'] == '612177'
    assert tags['size'] == '5510872'
    assert tags['avg_frame_rate'] == '288000/12019'
    assert tags['codec_name'] == 'h264'
    assert tags['width'] == '640'
    assert tags['height'] == '360'
    assert tags['nb_frames'] == '1440'
    assert tags['display_aspect_ratio'] == '16:9'
    assert tags['color_range'] == 'tv'

    # Undo
    ExtractMetadataTask().clean(deposit_id=dep_id,
                                version_id=obj_id)

    # Check that deposit's metadata got reverted
    record = Record.get_record(recid)
    assert 'extracted_metadata' not in record['_deposit']

    # Check that ObjectVersionTags were removed
    tags = ObjectVersion.query.first().get_tags()
    assert len(tags) == 0


def test_video_extract_frames(app, db, bucket, video_mp4):
    """Test extract frames from video."""
    obj = ObjectVersion.create(
        bucket=bucket, key='video.mp4', stream=open(video_mp4, 'rb'))
    version_id = str(obj.version_id)
    db.session.commit()

    task_s = ExtractFramesTask().s(version_id=version_id)

    # Extract frames
    task_s.delay()
    assert ObjectVersion.query.count() == 91  # master file + frames

    frames = ObjectVersion.query.join(ObjectVersion.tags).filter(
        ObjectVersionTag.key == 'master',
        ObjectVersionTag.value == version_id).all()
    assert len(frames) == 90

    # Undo
    ExtractFramesTask().clean(version_id=version_id)

    assert ObjectVersion.query.count() == 1  # master file
    frames = ObjectVersion.query.join(ObjectVersion.tags).filter(
        ObjectVersionTag.key == 'master',
        ObjectVersionTag.value == version_id).all()
    assert len(frames) == 0


def test_task_failure(celery_not_fail_on_eager_app, db, cds_depid, bucket):
    """Test SSE message for failure tasks."""
    app = celery_not_fail_on_eager_app
    sse_channel = 'test_channel'
    obj = ObjectVersion.create(bucket=bucket, key='test.pdf')

    class Listener(threading.Thread):
        def __init__(self):
            super(Listener, self).__init__()
            self._return = None

        def await(self):
            super(Listener, self).join()
            return self._return

        def run(self):
            from invenio_sse import current_sse
            with app.app_context():
                current_sse._pubsub.subscribe(sse_channel)
                messages = current_sse._pubsub.listen()
                next(messages)  # Skip subscribe message
                self._return = next(messages)['data'].decode('utf-8')

    # Establish connection
    listener = Listener()
    listener.start()
    time.sleep(1)

    ExtractMetadataTask().delay(
        uri='invalid_uri',
        version_id=str(obj.version_id),
        deposit_id=cds_depid,
        sse_channel=sse_channel)

    message = listener.await()
    assert '"state": "FAILURE"' in message
    assert 'ffprobe' in message


def test_transcode(db, bucket, mock_sorenson):
    """Test TranscodeVideoTask task."""
    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    filesize = 1024
    filename = 'test.mp4'
    preset_quality = '480p'
    new_filename = 'test[{0}].mp4'.format(preset_quality)
    obj = ObjectVersion.create(bucket, key=filename,
                               stream=BytesIO(b'\x00' * filesize))
    ObjectVersionTag.create(obj, 'display_aspect_ratio', '16:9')
    obj_id = str(obj.version_id)
    db.session.commit()
    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    task_s = TranscodeVideoTask().s(version_id=obj_id,
                                    preset_quality=preset_quality,
                                    sleep_time=0)

    # Transcode
    task_s.delay()

    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 2
    assert filename in keys
    assert new_filename in keys
    assert bucket.size == 2 * filesize

    # Undo
    TranscodeVideoTask().clean(version_id=obj_id,
                               preset_quality=preset_quality)

    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 1
    assert filename in keys
    assert new_filename not in keys
    assert bucket.size == filesize


def test_transcode_2tasks_delete1(db, bucket, mock_sorenson):
    """Test TranscodeVideoTask task when run 2 task and delete 1."""
    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    filesize = 1024
    filename = 'test.mp4'
    preset_qualities = ['480p', '720p']
    new_filenames = ['test[{0}].mp4'.format(p) for p in preset_qualities]

    (version_id, [task_s1, task_s2]) = transcode_task(
        bucket=bucket, filesize=filesize, filename=filename,
        preset_qualities=preset_qualities)

    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    # Transcode
    task_s1.delay()
    task_s2.delay()

    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 3
    assert new_filenames[0] in keys
    assert new_filenames[1] in keys
    assert filename in keys
    assert bucket.size == (3 * filesize)

    # Undo
    TranscodeVideoTask().clean(version_id=version_id,
                               preset_quality=preset_qualities[0])
    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 2
    assert new_filenames[0] not in keys
    assert new_filenames[1] in keys
    assert filename in keys
    assert bucket.size == (2 * filesize)
