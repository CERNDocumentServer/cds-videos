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

from cds.modules.ffmpeg import ff_frames, ff_probe, ff_probe_all, \
    valid_aspect_ratios


def test_ffprobe_mp4(video_mp4):
    """Test ff_probe wrapper."""
    assert float(ff_probe(video_mp4, 'duration')) == 60.095
    assert ff_probe(video_mp4, 'codec_type') == b'video'
    assert ff_probe(video_mp4, 'codec_name') == b'h264'
    assert int(ff_probe(video_mp4, 'width')) == 640
    assert int(ff_probe(video_mp4, 'height')) == 360
    assert int(ff_probe(video_mp4, 'bit_rate')) == 612177
    assert ff_probe(video_mp4, 'invalid') == b''


def test_ffprobe_mov(video_mov):
    """Test ff_probe wrapper."""
    assert float(ff_probe(video_mov, 'duration')) == 15.459
    assert ff_probe(video_mov, 'codec_type') == b'video'
    assert ff_probe(video_mov, 'codec_name') == b'h264'
    assert int(ff_probe(video_mov, 'width')) == 1280
    assert int(ff_probe(video_mov, 'height')) == 720
    assert int(ff_probe(video_mov, 'bit_rate')) == 1301440
    assert ff_probe(video_mov, 'invalid') == b''


def test_ffmpeg_mp4(video_mp4):
    """Test ffmpeg wrapper for extract frames."""
    tmp = tempfile.mkdtemp(dir=dirname(__file__))
    start, end = 5, 95
    ff_frames(video_mp4, start, end, 1, join(tmp, 'img%d.jpg'))
    file_no = len([f for f in listdir(tmp) if isfile(join(tmp, f))])
    assert file_no == end - start
    shutil.rmtree(tmp)


def test_ffmpeg_mov(video_mov):
    """Test ffmpeg wrapper for extract frames."""
    tmp = tempfile.mkdtemp(dir=dirname(__file__))
    start, end = 5, 95
    ff_frames(video_mov, start, end, 1, join(tmp, 'img%d.jpg'))
    file_no = len([f for f in listdir(tmp) if isfile(join(tmp, f))])
    assert file_no == end - start
    shutil.rmtree(tmp)


def test_ffprobe_all(online_video):
    """Test ff_probe_all wrapper."""
    information = json.loads(ff_probe_all(online_video))

    assert 'streams' in information
    video_stream = information['streams'][0]
    stream_keys = ['index', 'tags', 'bit_rate', 'codec_type', 'codec_name',
                   'start_time', 'duration']
    assert all([key in video_stream for key in stream_keys])

    assert 'format' in information
    format_keys = ['filename', 'nb_streams', 'format_name', 'format_long_name',
                   'start_time', 'duration', 'size', 'bit_rate', 'tags']
    assert all([key in information['format'] for key in format_keys])


def test_aspect_ratio(video_mp4, video_mov, online_video):
    """Test calculation of video's aspect ratio."""
    for video in [video_mp4, video_mov, online_video]:
        metadata = json.loads(ff_probe_all(video))['streams'][0]
        for aspect_ratio in [ff_probe(video, 'display_aspect_ratio'),
                             metadata['display_aspect_ratio']]:
            assert aspect_ratio in ['{}:{}'.format(w, h)
                                    for (w, h) in valid_aspect_ratios()]
