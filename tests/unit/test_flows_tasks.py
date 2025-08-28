# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2020 CERN.
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

import threading
import uuid

import mock
from cds.modules.flows.api import FlowService
import pytest
from celery import states
from celery.exceptions import Retry
from flask_security import login_user
from helpers import (
    add_video_tags,
    check_deposit_record_files,
    get_object_count,
    prepare_videos_for_publish,
    transcode_task,
)
from invenio_accounts.models import User
from invenio_files_rest.models import (
    Bucket,
    FileInstance,
    ObjectVersion,
    ObjectVersionTag,
)
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_records.models import RecordMetadata
from jsonschema.exceptions import ValidationError
from six import BytesIO
from sqlalchemy.orm.exc import ConcurrentModificationError
from werkzeug.utils import import_string

from cds.modules.deposit.api import (
    Project,
    Video,
    deposit_project_resolver,
    deposit_video_resolver,
)
from cds.modules.flows.models import FlowMetadata, FlowTaskMetadata
from cds.modules.flows.tasks import (
    DownloadTask,
    ExtractFramesTask,
    ExtractChapterFramesTask,
    ExtractMetadataTask,
    TranscodeVideoTask,
    sync_records_with_deposit_files,
    update_record,
)


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_download_to_object_version(db, bucket, users):
    """Test download to object version task."""
    with mock.patch("requests.get") as mock_request:
        obj = ObjectVersion.create(bucket=bucket, key="test.pdf")
        bid = bucket.id
        db.session.commit()

        # Mock download request
        file_size = 1024
        mock_request.return_value = type(
            "Response",
            (object,),
            {
                "raw": BytesIO(b"\x00" * file_size),
                "headers": {"Content-Length": file_size},
            },
        )
        assert obj.file is None

        # TODO CHECK
        flow = FlowMetadata(
            id=uuid.uuid4(), name="Test", user_id="1", deposit_id="test"
        )
        db.session.add(flow)
        task_model = FlowTaskMetadata.create(
            flow_id=flow.id,
            name=DownloadTask.name,
        )
        task_s = DownloadTask().s(
            "http://example.com/test.pdf",
            version_id=obj.version_id,
            task_id=str(task_model.id),
        )
        # Download
        task = task_s.delay()
        assert ObjectVersion.query.count() == 1
        obj = ObjectVersion.query.first()
        assert obj.key == "test.pdf"
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


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_update_record_thread(app, db):
    """Test update record with multiple concurrent transactions."""
    if db.engine.name == "sqlite":
        raise pytest.skip("Concurrent transactions are not supported nicely on SQLite")

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
                update_record.delay(
                    recid,
                    [
                        {
                            "op": "add",
                            "path": "/{}".format(self.path),
                            "value": self.value,
                        }
                    ],
                )

    # Run threads
    thread1 = RecordUpdater("test1", 1)
    thread2 = RecordUpdater("test2", 2)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Check that record was patched properly
    record = Record.get_record(recid)
    assert record.dumps() == {"test1": 1, "test2": 2}


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_update_record_retry(app, db):
    """Test update record with retry."""
    # Create record
    recid = str(Record.create({}).id)
    patch = [
        {
            "op": "add",
            "path": "/fuu",
            "value": "bar",
        }
    ]
    db.session.commit()
    with mock.patch(
        "invenio_records.api.Record.validate",
        side_effect=[ConcurrentModificationError, None],
    ) as mock_commit:
        with pytest.raises(Retry):
            update_record.s(recid=recid, patch=patch).apply()
        assert mock_commit.call_count == 2

    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert records[0].json == {"fuu": "bar"}


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_metadata_extraction_video(app, db, cds_depid, bucket, video):
    """Test metadata extraction video mp4."""
    recid = PersistentIdentifier.get("depid", cds_depid).object_uuid
    # simulate a no fully filled record
    record = Record.get_record(recid)
    if "title" in record:
        del record["title"]
    validator = "cds.modules.records.validators.PartialDraft4Validator"
    with pytest.raises(ValidationError):
        record.commit()
    record.commit(validator=import_string(validator))

    # Extract metadata
    obj = ObjectVersion.create(bucket=bucket, key="video.mp4")
    obj_id = str(obj.version_id)
    dep_id = str(cds_depid)
    with mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        task_s = ExtractMetadataTask().s(
            uri=video, version_id=obj_id, deposit_id=dep_id
        )
        task_s.delay()

    # Check that deposit's metadata got updated
    record = Record.get_record(recid)
    assert "extracted_metadata" in record["_cds"]
    assert record["_cds"]["extracted_metadata"]

    # Check that ObjectVersionTags were added
    tags = ObjectVersion.query.first().get_tags()
    assert tags["duration"] == "60.095000"
    assert tags["bit_rate"] == "612177"
    assert tags["avg_frame_rate"] == "288000/12019"
    assert tags["codec_name"] == "h264"
    assert tags["codec_long_name"] == "H.264 / AVC / MPEG-4 AVC / " "MPEG-4 part 10"
    assert tags["width"] == "640"
    assert tags["height"] == "360"
    assert tags["nb_frames"] == "1440"
    assert tags["display_aspect_ratio"] == "16:9"
    assert tags["color_range"] == "tv"

    # Undo
    ExtractMetadataTask().clean(deposit_id=dep_id, version_id=obj_id)

    # Check that deposit's metadata got reverted
    record = Record.get_record(recid)
    assert "extracted_metadata" not in record["_cds"]

    # Check that ObjectVersionTags are still there (attached to the old obj)
    tags = ObjectVersion.query.first().get_tags()
    assert len(tags) == 11

    # Simulate failed task, no extracted_metadata
    ExtractMetadataTask().clean(deposit_id=dep_id, version_id=obj_id)
    record = Record.get_record(recid)
    assert "extracted_metadata" not in record["_cds"]

    # check again tags
    tags = ObjectVersion.query.first().get_tags()
    assert len(tags) == 11


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_video_extract_frames(app, db, bucket, video):
    """Test extract frames from video."""
    obj = ObjectVersion.create(bucket=bucket, key="video.mp4", stream=open(video, "rb"))
    add_video_tags(obj)
    version_id = str(obj.version_id)
    db.session.commit()
    assert ObjectVersion.query.count() == 1

    with mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        task_s = ExtractFramesTask().s(version_id=version_id)
        # Extract frames
        task_s.delay()

    assert ObjectVersion.query.count() == get_object_count(transcode=False)

    frames_and_gif = (
        ObjectVersion.query.join(ObjectVersion.tags)
        .filter(ObjectVersionTag.key == "master", ObjectVersionTag.value == version_id)
        .all()
    )
    assert len(frames_and_gif) == get_object_count(download=False, transcode=False)
    assert ObjectVersion.query.count() == 12

    # Undo
    ExtractFramesTask().clean(version_id=version_id)

    # master file + create frames + delete frames
    assert ObjectVersion.query.count() == 23  # master file
    frames_and_gif = (
        ObjectVersion.query.join(ObjectVersion.tags)
        .filter(ObjectVersionTag.key == "master", ObjectVersionTag.value == version_id)
        .all()
    )
    assert len(frames_and_gif) == 11


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_transcode_too_high_resolutions(db, cds_depid):
    """Test trascoding task when it should discard some high resolutions."""
    bucket = deposit_project_resolver(cds_depid).files.bucket
    filesize = 1024
    filename = "test.mp4"
    preset_quality = "480p"
    obj = ObjectVersion.create(bucket, key=filename, stream=BytesIO(b"\x00" * filesize))
    ObjectVersionTag.create(obj, "display_aspect_ratio", "16:9")
    ObjectVersionTag.create(obj, "height", "360")
    ObjectVersionTag.create(obj, "width", "640")
    obj_id = str(obj.version_id)
    db.session.commit()

    with mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        task_s = TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset_quality, sleep_time=0
        )
        # Transcode
        result = task_s.delay(deposit_id=cds_depid)
        assert result.status == states.SUCCESS
        assert result.result == "Not transcoding for 480p"


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_transcode_and_undo(db, cds_depid):
    """Test TranscodeVideoTask task."""

    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    bucket = deposit_project_resolver(cds_depid).files.bucket
    filesize = 1024
    filename = "test.mp4"
    preset_quality = "480p"
    new_filename = "{0}.mp4".format(preset_quality)
    obj = ObjectVersion.create(bucket, key=filename, stream=BytesIO(b"\x00" * filesize))
    ObjectVersionTag.create(obj, "display_aspect_ratio", "16:9")
    obj_id = str(obj.version_id)
    db.session.commit()
    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    with mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        task_s = TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset_quality, sleep_time=0
        )
        # Transcode
        task_s.delay(deposit_id=cds_depid)

    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 2
    assert filename in keys
    assert new_filename in keys
    assert bucket.size == 2 * filesize

    # Undo
    TranscodeVideoTask().clean(version_id=obj_id, preset_quality=preset_quality)

    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 1
    assert filename in keys
    assert new_filename not in keys
    # file size doesn't change
    assert bucket.size == 2 * filesize


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_transcode_2tasks_delete1(db, cds_depid):
    """Test TranscodeVideoTask task when run 2 task and delete 1."""

    def get_bucket_keys():
        return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]

    bucket = deposit_project_resolver(cds_depid).files.bucket
    filesize = 1024
    filename = "test.mp4"
    preset_qualities = ["480p", "720p"]
    new_filenames = ["{0}.mp4".format(p) for p in preset_qualities]

    (version_id, [task_s1, task_s2]) = transcode_task(
        bucket=bucket,
        filesize=filesize,
        filename=filename,
        preset_qualities=preset_qualities,
    )

    assert get_bucket_keys() == [filename]
    assert bucket.size == filesize

    # Transcode
    with mock.patch("cds.modules.flows.tasks.Task.commit_status"):
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
    TranscodeVideoTask().clean(
        version_id=version_id, preset_quality=preset_qualities[0]
    )
    db.session.add(bucket)
    keys = get_bucket_keys()
    assert len(keys) == 2
    assert new_filenames[0] not in keys
    assert new_filenames[1] in keys
    assert filename in keys
    assert bucket.size == (3 * filesize)


# TODO: replace the tests to use opencast
# def test_transcode_ignore_exception_if_invalid(db, cds_depid):
#     """Test ignore exception if sorenson raise InvalidResolutionError."""
#     def get_bucket_keys():
#         return [o.key for o in list(ObjectVersion.get_by_bucket(bucket))]
#
#     bucket = deposit_project_resolver(cds_depid).files.bucket
#     filesize = 1024
#     filename = 'test.mp4'
#     preset_qualities = ['480p', '720p']
#
#     (version_id, [task_s1, task_s2]) = transcode_task(
#         bucket=bucket, filesize=filesize, filename=filename,
#         preset_qualities=preset_qualities)
#
#     assert get_bucket_keys() == [filename]
#     assert bucket.size == filesize
#
#     with mock.patch(
#         'cds.modules.flows.tasks.sorenson.start_encoding',
#         side_effect=InvalidResolutionError('fuu', 'test'),
#     ), mock.patch('cds.modules.flows.tasks.CeleryTask.commit_status'):
#         # Transcode
#         task = task_s1.delay(deposit_id=cds_depid)
#         isinstance(task.result, Ignore)


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
@pytest.mark.parametrize("preset, is_inside", [("1080ph265", None), ("240p", "true")])
def test_smil_tag(app, db, cds_depid, preset, is_inside):
    """Test that smil tags are generated correctly."""
    bucket = deposit_project_resolver(cds_depid).files.bucket

    def create_file(filename, preset_quality, aspect_ratio):
        obj = ObjectVersion.create(bucket, key=filename, stream=BytesIO(b"\x00" * 1024))
        ObjectVersionTag.create(obj, "display_aspect_ratio", aspect_ratio)
        return str(obj.version_id)

    # Setup and run the transcoding task
    obj_id = create_file("test.mp4", preset, "16:9")
    db.session.commit()

    with mock.patch(
        "cds.modules.flows.tasks.TranscodeVideoTask.on_success"
    ), mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset, sleep_time=0
        ).apply(deposit_id=cds_depid)

    # Get the tags from the newly created slave
    tags = (
        ObjectVersion.query.filter(ObjectVersion.version_id != obj_id)
        .first()
        .get_tags()
    )
    # Make sure the smil tag is set
    assert tags.get("smil") == is_inside


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
@pytest.mark.parametrize("preset, is_inside", [("1080ph265", "true"), ("240p", None)])
def test_download_tag(app, db, cds_depid, preset, is_inside):
    """Test that download tags are generated correctly."""
    bucket = deposit_project_resolver(cds_depid).files.bucket

    def create_file(filename, preset_quality, aspect_ratio):
        obj = ObjectVersion.create(bucket, key=filename, stream=BytesIO(b"\x00" * 1024))
        ObjectVersionTag.create(obj, "display_aspect_ratio", aspect_ratio)
        return str(obj.version_id)

    # Setup and run the transcoding task
    obj_id = create_file("test.mp4", preset, "16:9")
    db.session.commit()

    with mock.patch(
        "cds.modules.flows.tasks.TranscodeVideoTask.on_success"
    ), mock.patch("cds.modules.flows.tasks.Task.commit_status"):
        TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset, sleep_time=0
        ).apply(deposit_id=cds_depid)

    # Get the tags from the newly created slave
    tags = (
        ObjectVersion.query.filter(ObjectVersion.version_id != obj_id)
        .first()
        .get_tags()
    )
    # Make sure the download tag is set
    assert tags.get("download") == is_inside


# TODO: CHECK
@pytest.mark.skip(reason="TO BE CHECKED")
def test_sync_records_with_deposits(
    app, db, location, users, project_deposit_metadata, video_deposit_metadata
):
    """Test sync records with deposits task."""
    # create a project
    project = Project.create(project_deposit_metadata)
    project_deposit_metadata["report_number"] = ["123"]
    # create new video
    video_deposit_metadata["_project_id"] = project["_deposit"]["id"]
    deposit = Video.create(video_deposit_metadata)
    depid = deposit["_deposit"]["id"]

    # insert objects inside the deposit
    ObjectVersion.create(deposit.files.bucket, "obj_1").set_location(
        "mylocation1", 1, "mychecksum1"
    )
    ObjectVersion.create(deposit.files.bucket, "obj_2").set_location(
        "mylocation2", 1, "mychecksum2"
    )
    ObjectVersion.create(deposit.files.bucket, "obj_3").set_location(
        "mylocation3", 1, "mychecksum3"
    )
    obj_4 = ObjectVersion.create(deposit.files.bucket, "obj_4").set_location(
        "mylocation4", 1, "mychecksum4"
    )

    # publish
    login_user(User.query.get(users[0]))
    prepare_videos_for_publish([deposit])
    deposit = deposit.publish()
    _, record = deposit.fetch_published()
    assert deposit.is_published() is True

    # add a new object
    ObjectVersion.create(deposit.files.bucket, "obj_new").set_location(
        "mylocation_new", 1, "mychecksum"
    )
    # modify obj_1
    ObjectVersion.create(deposit.files.bucket, "obj_new").set_location(
        "mylocation2.1", 1, "mychecksum2.1"
    )
    # delete obj_3
    ObjectVersion.delete(deposit.files.bucket, "obj_3")
    # remove obj_4
    obj_4.remove()

    # check video and record
    files = ["obj_1", "obj_2", "obj_3", "obj_4"]
    edited_files = ["obj_1", "obj_2", "obj_3", "obj_new"]
    check_deposit_record_files(deposit, edited_files, record, files)

    # try to sync deposit and record
    sync_records_with_deposit_files.s(deposit_id=depid).apply_async()

    # get deposit and record
    deposit = deposit_video_resolver(depid)
    _, record = deposit.fetch_published()
    assert deposit.is_published() is True

    # check that record and deposit are sync
    re_edited_files = edited_files + ["obj_4"]
    check_deposit_record_files(deposit, edited_files, record, re_edited_files)


def test_extract_chapter_frames_task(app, db, bucket, video, users):
    """Test that chapter frames and chapters.vtt are created from description."""
    # Create a video object version
    obj = ObjectVersion.create(bucket=bucket, key="video.mp4", stream=open(video, "rb"))
    add_video_tags(obj)
    db.session.commit()
    
    # Create a project and video deposit with short chapter timestamps
    project_data = {
        "category": "OPEN",
        "type": "VIDEO",
    }
    project = Project.create(project_data)

    video_data = {
        "_project_id": project["_deposit"]["id"],
        "title": {"title": "Test Video with Chapters"},
        "description": """Test video with chapters:
            0:00 Introduction
            0:10 Chapter 1: Getting Started
            0:20 Chapter 2: Advanced Features
            0:30 Chapter 3: Examples
            0:40 Conclusion
            """,
        "contributors": [{"name": "Test User", "role": "Director"}],
    }
    video_deposit = Video.create(video_data)
    deposit_id = str(video_deposit["_deposit"]["id"])
    
    # Create flow metadata
    payload = dict(
        version_id=str(obj.version_id),
        key=obj.key,
        bucket_id=str(obj.bucket_id),
        deposit_id=deposit_id,
    )
    flow_metadata = FlowMetadata.create(
        deposit_id=deposit_id,
        user_id=users[0],
        payload=payload,
    )
    payload["flow_id"] = str(flow_metadata.id)
    flow_metadata.payload = payload
    flow = FlowService(flow_metadata)
    db.session.commit()

    # Expected chapter timestamps in seconds (0 becomes 0.1 offset)
    expected_timestamps = [0.1, 10, 20, 30, 40]

    # Mocks
    with mock.patch("cds.modules.flows.tasks.move_file_into_local") as mock_move, \
         mock.patch("cds.modules.flows.tasks.ff_frames") as mock_ff_frames, \
         mock.patch("cds.modules.flows.tasks.file_opener_xrootd") as mock_file_opener, \
         mock.patch("os.path.exists", return_value=True), \
         mock.patch("os.path.getsize", return_value=1024), \
         mock.patch("cds.modules.flows.tasks.sync_records_with_deposit_files"), \
         mock.patch.object(ExtractChapterFramesTask, "_base_payload", {"tags": {"duration": 500}}), \
         mock.patch("cds.modules.flows.tasks.ExtractFramesTask._create_object") as mock_create_object, \
         mock.patch("cds.modules.flows.tasks.ObjectVersion.create") as mock_obj_create, \
         mock.patch("cds.modules.flows.tasks.ObjectVersionTag.create") as mock_tag_create:

        mock_move.return_value.__enter__.return_value = "/tmp/test_video.mp4"
        mock_file_opener.return_value = BytesIO(b"fake_frame_data")

        fake_obj = mock.Mock()
        mock_obj_create.return_value = fake_obj

        # Run task
        ExtractChapterFramesTask().s(**payload.copy()).apply_async()
        
        # Ensure ff_frames was called once for each expected timestamp
        assert mock_ff_frames.call_count == len(expected_timestamps)
        call_args_list = [call[1] for call in mock_ff_frames.call_args_list]
        
        for i, call_args in enumerate(call_args_list):
            assert call_args["start"] == expected_timestamps[i]
            assert call_args["step"] == 1
        
        # Ensure _create_object was called for each chapter frame
        assert mock_create_object.call_count == len(expected_timestamps)
        
        # Verify all calls to _create_object had correct master_id
        for call_args in mock_create_object.call_args_list:
            kwargs = call_args.kwargs
            assert kwargs["master_id"] == obj.version_id
            assert kwargs["is_chapter_frame"] is True
            assert kwargs["context_type"] == "frame"
            assert kwargs["media_type"] == "image"

        # ---- Verify chapters.vtt creation ----
        mock_obj_create.assert_called_once()
        vtt_call_args = mock_obj_create.call_args
        assert vtt_call_args.kwargs["bucket"] == obj.bucket
        assert vtt_call_args.kwargs["key"] == "chapters.vtt"

        # Tags applied to chapters.vtt
        tag_keys = [c.args[1] for c in mock_tag_create.call_args_list]
        assert "context_type" in tag_keys
        assert "content_type" in tag_keys
        assert "media_type" in tag_keys


def test_extract_chapter_frames_task_cleanup(app, db, bucket, video, users):
    """Test that chapter frames are updated/cleaned when description changes."""

    # Create master ObjectVersion
    obj = ObjectVersion.create(bucket=bucket, key="video.mp4", stream=open(video, "rb"))
    add_video_tags(obj)
    db.session.commit()
    master_version_id = str(obj.version_id)

    # Create project + video deposit
    project = Project.create({"category": "OPEN", "type": "VIDEO"})
    video_deposit = Video.create({
        "_project_id": project["_deposit"]["id"],
        "title": {"title": "Video with chapters"},
        "description": """0:00 Intro
                          0:10 Chapter 1
                          0:20 Chapter 2""",
    })
    deposit_id = str(video_deposit["_deposit"]["id"])

    # Flow metadata
    payload = dict(
        version_id=master_version_id,
        key=obj.key,
        bucket_id=str(obj.bucket_id),
        deposit_id=deposit_id,
    )
    flow_metadata = FlowMetadata.create(
        deposit_id=deposit_id, user_id=users[0], payload=payload
    )
    payload["flow_id"] = str(flow_metadata.id)
    flow_metadata.payload = payload
    FlowService(flow_metadata)
    db.session.commit()

    with mock.patch("cds.modules.flows.tasks.move_file_into_local"), \
         mock.patch("cds.modules.flows.tasks.ff_frames"), \
         mock.patch("cds.modules.flows.tasks.file_opener_xrootd", return_value=BytesIO(b"fake_frame_data")), \
         mock.patch("os.path.exists", return_value=True), \
         mock.patch("os.path.getsize", return_value=1024), \
         mock.patch("cds.modules.flows.tasks.sync_records_with_deposit_files"), \
         mock.patch.object(ExtractChapterFramesTask, "_base_payload", {"tags": {"duration": 100}}), \
         mock.patch("cds.modules.flows.tasks.ExtractFramesTask._create_object") as mock_create_object, \
         mock.patch("cds.modules.flows.tasks.ExtractChapterFramesTask._build_chapter_vtt"), \
         mock.patch("cds.modules.flows.tasks.ExtractChapterFramesTask._get_existing_chapter_frame_timestamps") as mock_existing:

        # Track created & disposed timestamps (floats)
        created_timestamps = set()
        disposed_timestamps = []

        def fake_create_object(*args, **kwargs):
            if "timestamp" in kwargs:
                created_timestamps.add(float(kwargs["timestamp"]))
            return mock.Mock()

        def fake_clean(version_id, valid_chapter_seconds=None, *args, **kwargs):
            """Simulate cleaning: if 20.0 isn't in valid seconds, mark it disposed."""
            valid_floats = {float(s) for s in (valid_chapter_seconds or [])}
            if 20.0 not in valid_floats:
                disposed_timestamps.append(20.0)

        mock_create_object.side_effect = fake_create_object

        # First run → should create frames at 0.1, 10.0, 20.0
        mock_existing.return_value = set()
        with mock.patch("cds.modules.flows.tasks.ExtractChapterFramesTask.clean", side_effect=fake_clean):
            ExtractChapterFramesTask().s(**payload.copy()).apply_async()
        assert created_timestamps == {0.1, 10.0, 20.0}
        assert disposed_timestamps == []  # nothing disposed on first run

        # Update description → now chapters at 0.1, 10.0, 30.0
        video_deposit["description"] = """0:00 Intro
                                          0:10 Chapter 1
                                          0:30 Chapter 3"""
        video_deposit.commit()
        db.session.commit()

        # Reset state
        created_timestamps.clear()
        disposed_timestamps.clear()

        # Second run → should create 30.0, dispose 20.0
        mock_existing.return_value = {0.1, 10.0, 20.0}
        with mock.patch("cds.modules.flows.tasks.ExtractChapterFramesTask.clean", side_effect=fake_clean):
            ExtractChapterFramesTask().s(**payload.copy()).apply_async()

        assert 30.0 in created_timestamps
        assert 20.0 in disposed_timestamps


