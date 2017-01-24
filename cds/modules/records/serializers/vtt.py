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

"""VTT serializer for records."""

from __future__ import absolute_import, print_function

from datetime import datetime


class VTTSerializer(object):
    """Smil serializer for records."""

    @staticmethod
    def serialize(pid, record, links_factory=None):
        """Serialize a single record and persistent identifier.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        return VTT(record=record).format()


class VTT(object):
    """Smil formatter."""

    def __init__(self, record):
        """Initialize Smil formatter with the specific record."""
        self.record = record
        self.data = ""

    def format( self ):
        head = 'WEBVTT\n'
        thumbnail_data = self._format_frames( self.record )
        self.data = head+thumbnail_data
        return self.data

    def _format_frames( self , record):
        output = ''    # VTT string
        frames = record["_files"][0]["frame"]

        #sorts frames
        frames.sort(key = lambda s: s["key"])
        frames.sort(key = lambda s: len(s["key"]))

        #uses the 5, 15... 95 % frames
        usedFrames = [frames[int(round(float((10 * n) + 5)*len(frames)/100))-1] for n in range (10)]

        video_duration = float(record["_files"][0]["tags"]["duration"])
        thumbnail_Duration = round(float(video_duration/10),3)

        clipstart = 0
        clipend = clipstart + thumbnail_Duration
        
        for i in range(10):
            start = self.timeFormat(clipstart)
            end  = self.timeFormat(clipend)
            clipstart = clipend
            clipend += thumbnail_Duration

            #00:00.000 --> 00:00.000
            output += "\n" + start + " --> " + end + "\n"

            #frame_file_name.jpg
            output += usedFrames[i]["links"]["self"] + "\n"

        return output

    def timeFormat(self, seconds):
        d = datetime.utcfromtimestamp(seconds)
        s = d.strftime("%M.%S.%f")
        s = s[:-3]
        return s
