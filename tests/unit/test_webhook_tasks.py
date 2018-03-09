# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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

from jsonschema.exceptions import ValidationError
from flask_security import login_user
from celery import states
from werkzeug.utils import import_string
from invenio_accounts.models import User
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag, \
    Bucket, FileInstance
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_records.models import RecordMetadata
from six import BytesIO, next
from celery.exceptions import Retry, Ignore
from sqlalchemy.orm.exc import ConcurrentModificationError
from cds_sorenson.error import InvalidResolutionError

from cds.modules.webhooks.tasks import (DownloadTask,
                                        update_record, ExtractFramesTask,
                                        ExtractMetadataTask,
                                        TranscodeVideoTask,
                                        sync_records_with_deposit_files)
from cds.modules.deposit.api import deposit_video_resolver, Video, Project, \
    deposit_project_resolver

from helpers import add_video_tags, get_object_count, transcode_task, \
    check_deposit_record_files, prepare_videos_for_publish


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

        # Create + Delete
        assert ObjectVersion.query.count() == 2
        assert FileInstance.query.count() == 1


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


def test_metadata_extraction_video(app, db, cds_depid, bucket, video):
    """Test metadata extraction video mp4."""
    recid = PersistentIdentifier.get('depid', cds_depid).object_uuid
    # simulate a no fully filled record
    record = Record.get_record(recid)
    if 'title' in record:
        del record['title']
    validator = 'cds.modules.records.validators.PartialDraft4Validator'
    with pytest.raises(ValidationError):
        record.commit()
    record.commit(validator=import_string(validator))

    # Extract metadata
    obj = ObjectVersion.create(bucket=bucket, key='video.mp4')
    obj_id = str(obj.version_id)
    dep_id = str(cds_depid)
    task_s = ExtractMetadataTask().s(uri=video,
                                     version_id=obj_id,
                                     deposit_id=dep_id)
    task_s.delay()

    # Check that deposit's metadata got updated
    record = Record.get_record(recid)
    assert 'extracted_metadata' in record['_cds']
    assert record['_cds']['extracted_metadata']

    # Check that ObjectVersionTags were added
    tags = ObjectVersion.query.first().get_tags()
    assert tags['duration'] == '60.095000'
    assert tags['bit_rate'] == '612177'
    assert tags['avg_frame_rate'] == '288000/12019'
    assert tags['codec_name'] == 'h264'
    assert tags['codec_long_name'] == 'H.264 / AVC / MPEG-4 AVC / ' \
                                      'MPEG-4 part 10'
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
    assert 'extracted_metadata' not in record['_cds']

    # Check that ObjectVersionTags are still there (attached to the old obj)
    tags = ObjectVersion.query.first().get_tags()
    assert len(tags) == 11

    # Simulate failed task, no extracted_metadata
    ExtractMetadataTask().clean(deposit_id=dep_id,
                                version_id=obj_id)
    record = Record.get_record(recid)
    assert 'extracted_metadata' not in record['_cds']

    # check again tags
    tags = ObjectVersion.query.first().get_tags()
    assert len(tags) == 11


def test_video_extract_frames(app, db, bucket, video):
    """Test extract frames from video."""
    obj = ObjectVersion.create(
        bucket=bucket, key='video.mp4', stream=open(video, 'rb'))
    add_video_tags(obj)
    version_id = str(obj.version_id)
    db.session.commit()
    assert ObjectVersion.query.count() == 1

    task_s = ExtractFramesTask().s(version_id=version_id)

    # Extract frames
    task_s.delay()
    assert ObjectVersion.query.count() == get_object_count(transcode=False)

    frames_and_gif = ObjectVersion.query.join(ObjectVersion.tags).filter(
        ObjectVersionTag.key == 'master',
        ObjectVersionTag.value == version_id).all()
    assert len(frames_and_gif) == get_object_count(download=False,
                                                   transcode=False)
    assert ObjectVersion.query.count() == 12

    # Undo
    ExtractFramesTask().clean(version_id=version_id)

    # master file + create frames + delete frames
    assert ObjectVersion.query.count() == 23  # master file
    frames_and_gif = ObjectVersion.query.join(ObjectVersion.tags).filter(
        ObjectVersionTag.key == 'master',
        ObjectVersionTag.value == version_id).all()
    assert len(frames_and_gif) == 11


def test_transcode_too_high_resolutions(db, bucket):
    """Test trascoding task when it should discard some high resolutions."""
    filesize = 1024
    filename = 'test.mp4'
    preset_quality = '480p'
    obj = ObjectVersion.create(bucket, key=filename,
                               stream=BytesIO(b'\x00' * filesize))
    ObjectVersionTag.create(obj, 'display_aspect_ratio', '16:9')
    ObjectVersionTag.create(obj, 'height', 360)
    ObjectVersionTag.create(obj, 'width', 640)
    obj_id = str(obj.version_id)
    db.session.commit()

    task_s = TranscodeVideoTask().s(version_id=obj_id,
                                    preset_quality=preset_quality,
                                    sleep_time=0)

    # Transcode
    result = task_s.delay()
    assert result.status == states.IGNORED


def test_transcode_and_undo(db, cds_depid, mock_sorenson):
    """Test TranscodeVideoTask task."""
    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    bucket = deposit_project_resolver(cds_depid).files.bucket
    filesize = 1024
    filename = 'test.mp4'
    preset_quality = '480p'
    new_filename = '{0}.mp4'.format(preset_quality)
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
    task_s.delay(deposit_id=cds_depid)

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
    # file size doesn't change
    assert bucket.size == 2 * filesize


def test_transcode_2tasks_delete1(db, cds_depid, mock_sorenson):
    """Test TranscodeVideoTask task when run 2 task and delete 1."""
    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    bucket = deposit_project_resolver(cds_depid).files.bucket
    filesize = 1024
    filename = 'test.mp4'
    preset_qualities = ['480p', '720p']
    new_filenames = ['{0}.mp4'.format(p) for p in preset_qualities]

    (version_id, [task_s1, task_s2]) = transcode_task(
        bucket=bucket, filesize=filesize, filename=filename,
        preset_qualities=preset_qualities)

    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    # Transcode
    task_s1.delay(deposit_id=cds_depid)
    task_s2.delay(deposit_id=cds_depid)

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
    assert bucket.size == (3 * filesize)


def test_transcode_ignore_exception_if_invalid(db, bucket):
    """Test ignore exception if sorenson raise InvalidResolutionError."""
    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    filesize = 1024
    filename = 'test.mp4'
    preset_qualities = ['480p', '720p']

    (version_id, [task_s1, task_s2]) = transcode_task(
        bucket=bucket, filesize=filesize, filename=filename,
        preset_qualities=preset_qualities)

    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    with mock.patch('cds.modules.webhooks.tasks.start_encoding',
                    side_effect=InvalidResolutionError('fuu', 'test')):
        # Transcode
        task = task_s1.delay()
        isinstance(task.result, Ignore)


@pytest.mark.parametrize('preset, is_inside', [
    ('1080ph265', None), ('240p', 'true')
])
def test_smil_tag(app, db, bucket, mock_sorenson, preset, is_inside):
    """Test that smil tags are generated correctly."""
    def create_file(filename, preset_quality, aspect_ratio):
        obj = ObjectVersion.create(bucket, key=filename,
                                   stream=BytesIO(b'\x00' * 1024))
        ObjectVersionTag.create(obj, 'display_aspect_ratio', aspect_ratio)
        return str(obj.version_id)

    # Setup and run the transcoding task
    obj_id = create_file('test.mp4', preset, '16:9')
    db.session.commit()

    with mock.patch(
            'cds.modules.webhooks.tasks.TranscodeVideoTask.on_success'):
        TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset, sleep_time=0
        ).apply()

    # Get the tags from the newly created slave
    tags = ObjectVersion.query.filter(
        ObjectVersion.version_id != obj_id).first().get_tags()
    # Make sure the smil tag is set
    assert tags.get('smil') == is_inside


@pytest.mark.parametrize('preset, is_inside', [
    ('1080ph265', 'true'), ('240p', None)
])
def test_download_tag(app, db, bucket, mock_sorenson, preset, is_inside):
    """Test that download tags are generated correctly."""
    def create_file(filename, preset_quality, aspect_ratio):
        obj = ObjectVersion.create(bucket, key=filename,
                                   stream=BytesIO(b'\x00' * 1024))
        ObjectVersionTag.create(obj, 'display_aspect_ratio', aspect_ratio)
        return str(obj.version_id)

    # Setup and run the transcoding task
    obj_id = create_file('test.mp4', preset, '16:9')
    db.session.commit()

    with mock.patch(
            'cds.modules.webhooks.tasks.TranscodeVideoTask.on_success'):
        TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset, sleep_time=0
        ).apply()

    # Get the tags from the newly created slave
    tags = ObjectVersion.query.filter(
        ObjectVersion.version_id != obj_id).first().get_tags()
    # Make sure the download tag is set
    assert tags.get('download') == is_inside


def test_sync_records_with_deposits(app, db, location, users,
                                    project_deposit_metadata,
                                    video_deposit_metadata):
    """Test sync records with deposits task."""
    # create a project
    project = Project.create(project_deposit_metadata)
    project_deposit_metadata['report_number'] = ['123']
    # create new video
    video_deposit_metadata['_project_id'] = project['_deposit']['id']
    deposit = Video.create(video_deposit_metadata)
    depid = deposit['_deposit']['id']

    # insert objects inside the deposit
    ObjectVersion.create(
        deposit.files.bucket, "obj_1"
    ).set_location("mylocation1", 1, "mychecksum1")
    ObjectVersion.create(
        deposit.files.bucket, "obj_2"
    ).set_location("mylocation2", 1, "mychecksum2")
    ObjectVersion.create(
        deposit.files.bucket, "obj_3"
    ).set_location("mylocation3", 1, "mychecksum3")
    obj_4 = ObjectVersion.create(
        deposit.files.bucket, "obj_4"
    ).set_location("mylocation4", 1, "mychecksum4")

    # publish
    login_user(User.query.get(users[0]))
    prepare_videos_for_publish([deposit])
    deposit = deposit.publish()
    _, record = deposit.fetch_published()
    assert deposit.is_published() is True

    # add a new object
    ObjectVersion.create(
        deposit.files.bucket, "obj_new"
    ).set_location("mylocation_new", 1, "mychecksum")
    # modify obj_1
    ObjectVersion.create(
        deposit.files.bucket, "obj_new"
    ).set_location("mylocation2.1", 1, "mychecksum2.1")
    # delete obj_3
    ObjectVersion.delete(
        deposit.files.bucket, "obj_3")
    # remove obj_4
    obj_4.remove()

    # check video and record
    files = ['obj_1', 'obj_2', 'obj_3', 'obj_4']
    edited_files = ['obj_1', 'obj_2', 'obj_3', 'obj_new']
    check_deposit_record_files(deposit, edited_files, record, files)

    # try to sync deposit and record
    sync_records_with_deposit_files.s(deposit_id=depid).apply_async()

    # get deposit and record
    deposit = deposit_video_resolver(depid)
    _, record = deposit.fetch_published()
    assert deposit.is_published() is True

    # check that record and deposit are sync
    re_edited_files = edited_files + ['obj_4']
    check_deposit_record_files(deposit, edited_files, record,
                               re_edited_files)
