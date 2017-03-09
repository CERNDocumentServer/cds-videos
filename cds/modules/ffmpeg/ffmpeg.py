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

"""Python wrappers for the ffmpeg command-line utility."""

from __future__ import absolute_import

import json
from subprocess import check_output

import pexpect
from cds_sorenson.api import get_available_aspect_ratios
from flask import current_app


def ff_probe(input_filename, field):
    """Retrieve requested field from the output of ffprobe.

    **OPTIONS**

    * *-v error* show all errors
    * *-select_streams v:0* select only video stream
    * *-show_entries stream=<field>* show only requested field
    * *-of default=noprint_wrappers=1:nokey=1* extract only values
    """
    if field == 'display_aspect_ratio':
        return probe_aspect_ratio(input_filename)

    return check_output([
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream={}'.format(field),
        '-of', 'default=noprint_wrappers=1:nokey=1',
        '{}'.format(input_filename)
    ]).rstrip()


def ff_probe_all(input_filename):
    """Retrieve all video metadata from the output of ffprobe.

    **OPTIONS**

    * *-v error* show all errors
    * *-show_format -print_format json* output in JSON format
    * *-show_streams -select_streams v:0* show information for video streams
    """
    metadata = check_output([
        'ffprobe', '-v', 'error',
        '-show_format', '-print_format', 'json',
        '-show_streams', '-select_streams', 'v:0',
        '{}'.format(input_filename)
    ]).decode('utf-8')

    return _patch_aspect_ratio(metadata)


#
# Aspect Ratio  # TODO remove when Sorenson is updated
#
def probe_aspect_ratio(input_filename):
    """Probe video's aspect ratio, calculating it if needed."""
    metadata = ff_probe_all(input_filename)
    return json.loads(metadata)['streams'][0]['display_aspect_ratio']


def _calculate_aspect_ratio(width, height):
    """Calculate a video's aspect ratio from its dimensions."""
    ratios = get_available_aspect_ratios(pairs=True)
    for (w, h) in ratios:
        if w / h == width / height:
            return '{0}:{1}'.format(w, h)
    raise RuntimeError('Video dimensions do not correspond to any valid '
                       'aspect ratio.')


def _patch_aspect_ratio(metadata):
    """Replace invalid aspect ratio(i.e. '0:1') with calculated one."""
    info = json.loads(metadata)
    sinfo = info['streams'][0]
    key = 'display_aspect_ratio'
    if sinfo[key] == '0:1':
        sinfo[key] = _calculate_aspect_ratio(sinfo['width'], sinfo['height'])
    return json.dumps(info)


#
# Frame extraction
#
def ff_frames(input_file, start, end, step, duration, output,
              progress_callback=None):
    """Extract requested frames from video.

    :param input_file:
    :param start: time position to begin extracting frames.
    :param end: time position to stop extracting frames.
    :param step: time interval between frames.
    :param duration: total duration of the video
    :param output: output folder and format for the file names as in ``ffmpeg``
    , i.e /path/to/somewhere/frames-%d.jpg
    :param progress_callback: function taking as first parameter the number of
    seconds processed and as second parameter the total duration of the video.
    """
    cmd = 'ffmpeg -i {0} -ss {1} -to {2} -vf fps=1/{3} {4}'.format(
        input_file, start, end, step, output
    )

    if current_app.config.get('USE_EOS', False):
        cmd = 'bash -c "eosfusebind && {}"'.format(cmd)

    thread = pexpect.spawn(cmd)

    regex = thread.compile_pattern_list(
        [pexpect.EOF, 'time=(\d\d:\d\d:\d\d).\d\d']
    )
    while True:
        index = thread.expect_list(regex, timeout=None)
        if index == 0:
            break
        elif progress_callback:
            progress_callback(sum(
                int(amount) * 60 ** power for power, amount in
                enumerate(reversed(thread.match.group(1).split(b':')))
            ), duration)
