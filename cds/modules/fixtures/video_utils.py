# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Fixture Modules."""


import json

from invenio_files_rest.models import Bucket, ObjectVersion, ObjectVersionTag

from ..records.utils import to_string


def _create_tags(video_obj, **tags):
    """Create multiple tags for a single object version."""
    [ObjectVersionTag.create(video_obj, tag, to_string(tags[tag])) for tag in tags]


def add_master_to_video(video_deposit, filename, stream, video_duration):
    """Add a master file inside video."""
    video_bucket = Bucket.get(video_deposit["_buckets"]["deposit"])
    # Master video
    master_obj = ObjectVersion.create(bucket=video_bucket, key=filename, stream=stream)
    _create_tags(
        master_obj,
        display_aspect_ratio="16:9",
        bit_rate="959963",
        codec_name="h264",
        codec_long_name="H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
        duration=video_duration,
        nb_framesr="1557",
        size="10498667",
        media_type="video",
        context_type="master",
        avg_frame_rate="25/1",
        width="1280",
        height="720",
    )
    return str(master_obj.version_id)
