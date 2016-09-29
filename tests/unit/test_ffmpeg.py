# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""CDS FFmpeg tests."""

from __future__ import absolute_import

import shutil
import tempfile
from os import listdir
from os.path import isfile, join, dirname
import json
from cds.modules.webhooks.ffmpeg import ff_frames, ff_probe, ff_probe_all


def test_ffprobe(video):
    """Test ff_probe wrapper."""
    assert float(ff_probe(video, 'duration')) == 60.095
    assert ff_probe(video, 'codec_type') == b'video'
    assert ff_probe(video, 'codec_name') == b'h264'
    assert int(ff_probe(video, 'width')) == 640
    assert int(ff_probe(video, 'height')) == 360
    assert int(ff_probe(video, 'bit_rate')) == 612177
    assert ff_probe(video, 'invalid') == b''


def test_ffprobe_all(online_video):
    """Test ff_probe_all wrapper."""
    information = json.loads(ff_probe_all(online_video))
    assert 'streams' in information
    for stream in information['streams']:
        stream_keys = ['index', 'tags', 'bit_rate', 'codec_type',
                       'start_time', 'duration']
        assert all([key in stream for key in stream_keys])
        if stream['codec_type'] in ['audio', 'video']:
            assert 'codec_name' in stream
    assert 'format' in information
    format_keys = ['filename', 'nb_streams', 'format_name', 'format_long_name',
                   'start_time', 'duration', 'size', 'bit_rate', 'tags']
    assert all([key in information['format'] for key in format_keys])


def test_ffmpeg(video):
    """Test ffmpeg wrapper for extract frames."""
    tmp = tempfile.mkdtemp(dir=dirname(__file__))
    list(ff_frames(video, 25, 45, 1, join(tmp, 'img%d.jpg')))
    file_no = len([f for f in listdir(tmp) if isfile(join(tmp, f))])
    assert file_no == 20
    shutil.rmtree(tmp)
