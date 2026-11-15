# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2026 CERN.
#
# CDS is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.

"""Records for the end to end tests.

Creates two projects of the test user, a published one with two videos
and a draft one with a video, with the files of processed videos (master
file, subformats, frames, subtitles and an additional file), and indexes
them. It needs the users, the categories and the licenses of
``tests/e2e/setup.sh`` and runs in the environment of the instance::

    python tests/e2e/seed.py
"""

import io
import os

from flask_security import login_user
from invenio_accounts.models import User
from invenio_app.factory import create_app
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_indexer.api import RecordIndexer
from invenio_records.models import RecordMetadata
from invenio_search import current_search_client
from PIL import Image, ImageDraw

CLIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "clip.mp4")

# ffprobe of data/clip.mp4
CLIP_METADATA = {
    "duration": "2.000000",
    "width": "320",
    "height": "240",
    "bit_rate": "55324",
    "codec_name": "h264",
    "avg_frame_rate": "24/1",
    "display_aspect_ratio": "4:3",
    "nb_frames": "48",
}

SUBTITLES = """WEBVTT

00:00:00.000 --> 00:00:01.000
The test clip starts

00:00:01.000 --> 00:00:02.000
The test clip ends
"""

KEYWORDS = [("ATLAS", "1000"), ("detector", "1001"), ("higgs", "1002")]

CONTRIBUTORS = [
    {"name": "Doe, Jane", "role": "Director", "affiliations": ["CERN"]},
    {"name": "Doe, John", "role": "Camera Operator"},
]

LICENSE = [{"license": "CERN", "url": "http://copyright.web.cern.ch"}]


def frame(index):
    """A JPEG frame of the clip."""
    image = Image.new("RGB", (320, 240), (20 * index, 80, 160))
    ImageDraw.Draw(image).text((20, 20), "Frame {0}".format(index), fill="white")
    return image


def encode(image, image_format="JPEG", **kwargs):
    """The bytes of an image."""
    data = io.BytesIO()
    image.save(data, image_format, **kwargs)
    return data.getvalue()


def add_object(bucket_id, key, data, tags):
    obj = ObjectVersion.create(bucket_id, key, stream=io.BytesIO(data), size=len(data))
    for name, value in tags.items():
        ObjectVersionTag.create(obj, name, str(value))
    return obj


def add_files(video, subtitles=True):
    """The files of a video after the upload and the processing tasks."""
    bucket_id = video["_buckets"]["deposit"]
    with open(CLIP, "rb") as fp:
        clip = fp.read()
    master = add_object(
        bucket_id,
        "clip.mp4",
        clip,
        dict(
            CLIP_METADATA,
            media_type="video",
            context_type="master",
            preview="true",
            content_type="mp4",
        ),
    )
    master_id = str(master.version_id)
    frames = [frame(index) for index in range(1, 11)]
    for index, image in enumerate(frames, start=1):
        add_object(
            bucket_id,
            "frame-{0}.jpg".format(index),
            encode(image),
            {
                "media_type": "image",
                "context_type": "frame",
                "master": master_id,
                "content_type": "jpg",
                "timestamp": str((index - 1) * 0.2),
            },
        )
    add_object(
        bucket_id,
        "frames.gif",
        encode(frames[0], "GIF", save_all=True, append_images=frames[1:]),
        {
            "media_type": "image",
            "context_type": "frames-preview",
            "master": master_id,
            "content_type": "gif",
        },
    )
    for quality, width, height in (("240p", 320, 240), ("360p", 480, 360)):
        add_object(
            bucket_id,
            "clip-{0}.mp4".format(quality),
            clip,
            {
                "media_type": "video",
                "context_type": "subformat",
                "master": master_id,
                "content_type": "mp4",
                "preset_quality": quality,
                "width": width,
                "height": height,
                "video_bitrate": "49656",
                "smil": "true",
            },
        )
    if subtitles:
        add_object(
            bucket_id,
            "clip_en.vtt",
            SUBTITLES.encode("utf-8"),
            {
                "context_type": "subtitle",
                "media_type": "subtitle",
                "content_type": "vtt",
                "language": "en",
            },
        )
    add_object(
        bucket_id,
        "notes.txt",
        b"Notes about the clip.\n",
        {
            "context_type": "additional_file",
            "media_type": "text",
            "content_type": "txt",
        },
    )


def processed(video):
    """Mark the processing tasks of a video as done."""
    video["_cds"]["extracted_metadata"] = dict(
        CLIP_METADATA, title="Test clip", keywords=["test"]
    )
    video["_cds"]["state"] = {
        "file_upload": "SUCCESS",
        "file_video_metadata_extraction": "SUCCESS",
        "file_video_extract_frames": "SUCCESS",
        "file_transcode": "SUCCESS",
    }
    video["_files"] = video.files.dumps()
    return video


def keywords(*names):
    ids = dict(KEYWORDS)
    return [{"name": name, "key_id": ids[name]} for name in names]


def create_project(metadata, videos):
    """A draft project with processed videos: (metadata, subtitles) pairs."""
    from cds.modules.deposit.api import Project, Video

    project = Project.create(
        dict(
            metadata,
            contributors=CONTRIBUTORS[:1],
            license=LICENSE,
            _access={"update": ["test@test.ch"]},
        )
    ).commit()
    for video_metadata, subtitles in videos:
        video = Video.create(
            dict(
                video_metadata,
                _project_id=project["_deposit"]["id"],
                contributors=CONTRIBUTORS,
                copyright={"holder": "CERN", "year": "2026"},
                license=LICENSE,
                language="en",
            )
        )
        add_files(video, subtitles=subtitles)
        processed(video).commit()
    db.session.commit()
    return Project.get_record(project.id)


def seed():
    from cds.modules.records.api import Keyword

    indexer = RecordIndexer()
    for name, key_id in KEYWORDS:
        keyword = Keyword.create({"name": name, "key_id": key_id})
        db.session.commit()
        indexer.index(keyword)

    login_user(User.query.filter_by(email="test@test.ch").one())
    published = create_project(
        {
            "title": {"title": "End to end tests"},
            "description": "A project for the end to end tests.",
            "category": "ATLAS",
            "type": "VIDEO",
            "keywords": keywords("ATLAS"),
            "date": "2026-01-15",
        },
        [
            (
                {
                    "title": {"title": "Assembling the tile calorimeter"},
                    "description": (
                        "This video is about the <b>tile calorimeter</b> of the "
                        "ATLAS detector."
                    ),
                    "date": "2026-01-15",
                    "keywords": keywords("ATLAS", "detector"),
                },
                True,
            ),
            (
                {
                    "title": {"title": "Higgs boson explained"},
                    "description": "An animation about the Higgs mechanism.",
                    "date": "2026-01-10",
                    "keywords": keywords("higgs"),
                },
                False,
            ),
        ],
    )
    published.publish().commit()
    db.session.commit()
    create_project(
        {
            "title": {"title": "Draft of the end to end tests"},
            "description": "A project that is not published yet.",
            "category": "CERN",
            "type": "FOOTAGE",
        },
        [
            (
                {
                    "title": {"title": "Draft video ready to publish"},
                    "description": "Everything is processed.",
                    "date": "2026-02-01",
                },
                True,
            )
        ],
    )

    ids = [str(record.id) for record in RecordMetadata.query.all()]
    indexer.bulk_index(ids)
    indexer.process_bulk_queue()
    current_search_client.indices.refresh()
    return len(ids)


def main():
    app = create_app()
    with app.app_context(), app.test_request_context():
        print("Indexed {0} records".format(seed()))


if __name__ == "__main__":
    main()
