# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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

import pytest
from cds.modules.ffmpeg import ff_frames, ff_probe, ff_probe_all
from cds.modules.ffmpeg.errors import FrameExtractionInvalidArguments
from cds_sorenson.api import get_available_aspect_ratios


def test_ffprobe(video):
    """Test ff_probe wrapper."""
    expected_info = dict(
        codec_type=b'video',
        codec_name=b'h264',
        duration=60.095,
        width=640,
        height=360,
        bit_rate=612177,
        invalid=b'',
    )

    def check_metadata(field_name, convertor=lambda x: x, e=None):
        expected = expected_info[field_name]
        actual = convertor(ff_probe(video, field_name))
        if e is None:
            assert expected == actual
        else:
            assert expected - e < actual < expected + e

    check_metadata('codec_type')
    check_metadata('codec_name')
    check_metadata('invalid')
    check_metadata('width', convertor=int)
    check_metadata('height', convertor=int)
    check_metadata('bit_rate', convertor=int)
    check_metadata('duration', convertor=float, e=0.2)


@pytest.mark.parametrize('start, end, step, error', [
    (5, 95, 10, None),  # CDS use-case
    (4, 88, 12, None),
    (1, 89, 1, None),
    (90, 98, 2, None),
    (0, 100, 1, FrameExtractionInvalidArguments),
    (5, 10, 2, FrameExtractionInvalidArguments),
])
def test_frames(video_with_small, start, end, step, error):
    """Test frame extraction."""
    frame_indices = []
    tmp = tempfile.mkdtemp(dir=dirname(__file__))

    # Convert percentages to values
    duration = float(ff_probe(video_with_small, 'duration'))
    time_step = duration * step / 100
    start_time = duration * start / 100
    end_time = (duration * end / 100) + 0.01

    arguments = dict(
        input_file=video_with_small,
        start=start_time,
        end=end_time,
        step=time_step,
        duration=duration,
        output=join(tmp, 'img{0:02d}.jpg'),
        progress_callback=lambda i: frame_indices.append(i))

    # Extract frames
    if error:
        with pytest.raises(error):
            ff_frames(**arguments)
    else:
        ff_frames(**arguments)

        # Check that progress updates are complete
        expected_file_no = ((end - start) / step) + 1
        assert frame_indices == range(1, expected_file_no + 1)

        # Check number of generated files
        file_no = len([f for f in listdir(tmp) if isfile(join(tmp, f))])
        assert file_no == expected_file_no

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


def test_aspect_ratio(video, online_video):
    """Test calculation of video's aspect ratio."""
    for video in [video, online_video]:
        metadata = json.loads(ff_probe_all(video))['streams'][0]
        for aspect_ratio in [ff_probe(video, 'display_aspect_ratio'),
                             metadata['display_aspect_ratio']]:
            assert aspect_ratio in get_available_aspect_ratios()
