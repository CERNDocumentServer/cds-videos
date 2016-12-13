# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2015, 2016 CERN.
#
# Zenodo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Zenodo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Zenodo. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""Smil serializer for records."""

from __future__ import absolute_import, print_function

import textwrap

import six
from dateutil.parser import parse as iso2dt
from flask import current_app
from slugify import slugify
import json
# import xml.dom.minidom as xml_pp


class SmilSerializer(object):
    """Smil serializer for records."""

    @staticmethod
    def serialize(pid, record, links_factory=None):
        """Serialize a single record and persistent identifier.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        return Smil(record=record).format()


class Smil(object):
    """Smil formatter."""

    def __init__(self, record):
        """Initialize Smil formatter with the specific record."""
        self.record = record
        self.data = ""

    def format(self):
        """Returns the contents of the smil file as a string"""
        head = ('<smil>\n\t<head>\n\t\t'
                '<meta base="rtmp://wowza.cern.ch/vod/smil:Video"/>'
                '\n\t</head>\n\t<body>\n\t\t<switch>')
        tail = '\n\t\t</switch>\n\t</body>\n</smil>'
        video_data = self._format_videos(self.record)
        self.data = head+video_data+tail
        # xml = xml_pp.parseString(self.data)
        # self.data = xml.toprettyxml()
        return self.data

    @staticmethod
    def _format_videos(record):
        """Formats each video subformat"""
        output = ''    # Smil string
        for file in record["_files"]:
            for video in file["video"]:
                src = video["links"]["self"]
                bitrate = file["tags"]["bit_rate"]
                width = file["tags"]["width"]
                height = file["tags"]["height"]
                output += ('\n\t\t\t<video src="' + src +
                           '" system-bitrate="' + bitrate +
                           '" width="' + width +
                           '" height="' + height +
                           '"/>')
        return output
