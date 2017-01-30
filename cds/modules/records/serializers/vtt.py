# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
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

from __future__ import absolute_import, print_function

from datetime import datetime
from flask import render_template
from cds.modules.deposit.api import Video
from invenio_rest.errors import RESTValidationError, FieldError


class VTTSerializer(object):
    """Smil serializer for records."""

    @staticmethod
    def serialize(pid, record, links_factory=None):
        """Serialize a single record and persistent identifier.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        if record['$schema'] != Video.get_record_schema():
            raise RESTValidationError(errors=[FieldError(
                str(record.id), 'Unsupported format')])
        return VTT(record=record).format()


class VTT(object):
    """Smil formatter."""

    def __init__(self, record):
        """Initialize Smil formatter with the specific record."""
        self.record = record
        self.data = ""

    def format(self):
        thumbnail_data = self._format_frames(self.record)
        return render_template('cds_records/thumbnails.vtt',
                               frames=thumbnail_data)

    @staticmethod
    def _format_frames(record):
        """Select frames and format the start/end times."""
        thumbnail_data = []
        frames = record["_files"][0]["frame"]

        # sorts frames
        frames.sort(key=lambda s: s["key"])
        frames.sort(key=lambda s: len(s["key"]))

        # uses the 5, 15... 95 % frames
        used_frames = [frames[int(round(float((10 * n) + 5) *
                       len(frames)/100))-1] for n in range(10)]

        video_duration = float(record["_files"][0]["tags"]["duration"])
        thumbnail_duration = round(float(video_duration/10), 3)

        clipstart = 0
        clipend = clipstart + thumbnail_duration

        for i in range(10):
            start = VTT.time_format(clipstart)
            end = VTT.time_format(clipend)
            clipstart = clipend
            clipend += thumbnail_duration
            file = used_frames[i]["links"]["self"]
            info = {}
            info['start_time'] = start
            info['end_time'] = end
            info['file_name'] = file
            thumbnail_data.append(info)
        return thumbnail_data

    @staticmethod
    def time_format(seconds):
        """Helper function to convert seconds to vtt time format"""
        d = datetime.utcfromtimestamp(seconds)
        s = d.strftime("%M.%S.%f")
        s = s[:-3]
        return s
