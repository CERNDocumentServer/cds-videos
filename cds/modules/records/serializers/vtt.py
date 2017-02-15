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

from __future__ import absolute_import, print_function

from datetime import datetime

from flask import current_app
from flask import render_template
from cds.modules.deposit.api import Video, CDSFilesIterator
from flask import url_for
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
        self.data = ''

    def format(self):
        thumbnail_data = self._format_frames(self.record)
        return render_template('cds_records/thumbnails.vtt',
                               frames=thumbnail_data)

    @staticmethod
    def _format_frames(record):
        """Select frames and format the start/end times."""
        thumbnail_data = []
        master_file = CDSFilesIterator.get_master_video_file(record)
        frames = CDSFilesIterator.get_video_frames(master_file)

        last_timestamp = float(master_file['tags']['duration'])
        for frame in frames[::-1]:
            timestamp = float(frame['tags']['timestamp'])
            start = VTT.time_format(timestamp)
            end = VTT.time_format(last_timestamp)
            thumbnail_size = current_app.config['VIDEO_POSTER_SIZE']
            file_name = url_for(
                'iiifimageapi',
                version='v2',
                uuid='{0}:{1}'.format(frame['bucket_id'], frame['key']),
                region='full',
                size='{0[0]},{0[1]}'.format(thumbnail_size),
                rotation='0',
                quality='default',
                image_format='png',
                _external=True)
            info = dict(
                start_time=start,
                end_time=end,
                file_name=file_name)
            thumbnail_data.append(info)
            last_timestamp = timestamp
        return thumbnail_data[::-1]

    @staticmethod
    def time_format(seconds):
        """Helper function to convert seconds to vtt time format."""
        d = datetime.utcfromtimestamp(seconds)
        s = d.strftime('%M:%S.%f')
        return s[:-3]
