# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# CDS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CDS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""VTT serializer for records."""


from datetime import datetime

from flask import current_app, render_template
from invenio_rest.errors import FieldError, RESTValidationError

from ...deposit.api import Video
from ..api import CDSVideosFilesIterator


class VTTSerializer(object):
    """Smil serializer for records."""

    @staticmethod
    def serialize(pid, record, links_factory=None):
        """Serialize a single record and persistent identifier.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        if record["$schema"] != Video.get_record_schema():
            raise RESTValidationError(
                errors=[FieldError(str(record.id), "Unsupported format")]
            )
        return VTT(record=record).format()


class VTT(object):
    """VTT thumbnail track formatter.

    Prefers sprite-sheet cues (``context_type=sprite``) which use WebVTT media
    fragment syntax (``URL#xywh=x,y,w,h``) so the browser only fetches a
    small number of grid images instead of one image per second.  Falls back
    to the legacy per-frame IIIF approach when no sprites are present.
    """

    def __init__(self, record):
        """Initialize VTT formatter with the specific record."""
        self.record = record
        self.data = ""

    def format(self):
        master_file = CDSVideosFilesIterator.get_master_video_file(self.record)
        sprites = CDSVideosFilesIterator.get_video_sprites(master_file)
        if sprites:
            thumbnail_data = self._format_sprite_cues(master_file, sprites)
        else:
            thumbnail_data = self._format_frame_cues(self.record, master_file)
        return render_template("cds_records/thumbnails.vtt", frames=thumbnail_data)

    @staticmethod
    def _format_sprite_cues(master_file, sprites):
        """Build per-second VTT cues from sprite sheets using #xywh= fragments.

        Each cue points into a cell of the sprite grid via the WebVTT / W3C
        media fragment ``#xywh=x,y,width,height`` syntax, which is supported
        by Video.js and other major players without any extra HTTP requests.
        """
        duration = float(master_file["tags"]["duration"])
        site_url = current_app.config.get("THEME_SITEURL", "")
        cues = []

        for sprite in sprites:
            tags = sprite["tags"]
            cols = int(tags["sprite_cols"])
            rows = int(tags["sprite_rows"])
            w = int(tags["thumb_width"])
            h = int(tags["thumb_height"])
            start_second = int(tags["start_second"])
            frames_per_sprite = int(tags["frames_per_sprite"])

            sprite_url = "{}/api/files/{}/{}".format(
                site_url, sprite["bucket_id"], sprite["key"]
            )

            for i in range(frames_per_sprite):
                second = start_second + i
                if second >= duration:
                    break
                col = i % cols
                row = i // cols
                x = col * w
                y = row * h
                cues.append({
                    "start_time": VTT.time_format(float(second)),
                    "end_time": VTT.time_format(min(float(second + 1), duration)),
                    "file_name": "{}#xywh={},{},{},{}".format(
                        sprite_url, x, y, w, h
                    ),
                })

        return cues

    @staticmethod
    def _format_frame_cues(record, master_file):
        """Legacy per-frame cues via IIIF image URLs (fallback)."""
        from invenio_iiif.utils import ui_iiif_image_url

        frames = [
            {
                "time": float(f["tags"]["timestamp"]),
                "bucket": f["bucket_id"],
                "key": f["key"],
                "version_id": f["version_id"],
            }
            for f in CDSVideosFilesIterator.get_video_frames(master_file)
        ]

        last_time = float(master_file["tags"]["duration"])
        poster_size = current_app.config["VIDEO_POSTER_SIZE"]
        site_url = current_app.config.get("THEME_SITEURL", "")
        frames_tail = frames[1:] + [{"time": last_time}]
        return [
            {
                "start_time": VTT.time_format(f["time"] if i > 0 else 0.0),
                "end_time": VTT.time_format(next_f["time"]),
                "file_name": "{}{}".format(
                    site_url,
                    ui_iiif_image_url(
                        f,
                        size="!{0[0]},{0[1]}".format(poster_size),
                        image_format="png",
                    ),
                ),
            }
            for i, (f, next_f) in enumerate(zip(frames, frames_tail))
        ]

    @staticmethod
    def time_format(seconds):
        """Helper function to convert seconds to vtt time format."""
        d = datetime.utcfromtimestamp(seconds)
        s = d.strftime("%H:%M:%S.%f")
        return s[:-3]
