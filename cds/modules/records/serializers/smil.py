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

"""Smil serializer for records."""

from __future__ import absolute_import, print_function

from flask import render_template
from cds.modules.deposit.api import Video
from invenio_rest.errors import RESTValidationError, FieldError


class SmilSerializer(object):
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
        return Smil(record=record).format()


class Smil(object):
    """Smil formatter."""

    def __init__(self, record):
        """Initialize Smil formatter with the specific record."""
        self.record = record
        self.data = ""

    def format(self):
        """Return the contents of the smil file as a string."""
        videos_data = self._format_videos(self.record)
        return render_template('cds_records/video.smil', videos=videos_data)

    @staticmethod
    def _format_videos(record):
        """Format each video subformat."""
        def get_option(info, key, value):
            if value:
                info[key] = value
            return info
        videos = []
        for file in record["_files"]:
            tags = file.get('tags', {})
            bit_rate = tags.get('bit_rate')
            width = tags.get('width')
            height = tags.get('height')
            for video in file.get('video', []):
                info = {}
                info = get_option(
                    info, 'src', video.get('links', {}).get('self'))
                info = get_option(info, 'bit_rate', bit_rate)
                info = get_option(info, 'width', width)
                info = get_option(info, 'height', height)
                videos.append(info)
        return videos
