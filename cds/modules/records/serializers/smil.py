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

"""Smil serializer for records."""

from __future__ import absolute_import, print_function

from flask import render_template
from invenio_db import db
from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)
from invenio_rest.errors import FieldError, RESTValidationError
from six import BytesIO

from ...deposit.api import Video
from ...previewer.api import get_relative_path
from ..api import CDSVideosFilesIterator


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

    def format(self):
        """Return the contents of the smil file as a string."""
        videos_data = self._format_videos(self.record)
        return render_template('cds_records/video.smil', videos=videos_data)

    @staticmethod
    def _format_videos(record):
        """Format each video subformat."""
        master_file = CDSVideosFilesIterator.get_master_video_file(record)
        for video in CDSVideosFilesIterator.get_video_subformats(master_file):
            tags = video['tags']
            # If the 'smil' config variable is False,
            # don't add this video to the SMIL file
            if tags.get('smil', True):
                yield dict(
                    src=get_relative_path(video['version_id']),
                    width=tags['width'],
                    height=tags['height'],
                    bit_rate=tags['video_bitrate']
                )


def generate_smil_file(record_id, record, bucket, master_object):
    """Generate SMIL file for Video record (on publish)."""
    #  output_folder = tempfile.mkdtemp()
    master_object = as_object_version(master_object)

    # Generate SMIL file
    master_key = master_object.key
    smil_key = '{0}.smil'.format(master_key.rsplit('.', 1)[0])
    smil_content = SmilSerializer.serialize(record_id, record)

    # Create ObjectVersion for SMIL file
    with db.session.begin_nested():
        obj = ObjectVersion.create(
            bucket=bucket,
            key=smil_key,
            stream=BytesIO(smil_content.encode()))
        ObjectVersionTag.create(obj, 'master', str(master_object.version_id))
        ObjectVersionTag.create(obj, 'context_type', 'playlist')
        ObjectVersionTag.create(obj, 'media_type', 'text')
