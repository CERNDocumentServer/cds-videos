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
from flask import current_app as app
from itertools import count, takewhile
from subprocess import STDOUT, CalledProcessError, check_output

from cds_sorenson.api import get_available_aspect_ratios
from .errors import FrameExtractionInvalidArguments, FFmpegExecutionError, \
    MetadataExtractionExecutionError, FrameExtractionExecutionError


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

    return run_command(
        'ffprobe -v error -select_streams v:0 -show_entries stream={0} -of '
        'default=noprint_wrappers=1:nokey=1 {1}'.format(field, input_filename),
        error_class=MetadataExtractionExecutionError
    ).rstrip()


def ff_probe_all(input_filename):
    """Retrieve all video metadata from the output of ffprobe.

    **OPTIONS**

    * *-v error* show all errors
    * *-show_format -print_format json* output in JSON format
    * *-show_streams -select_streams v:0* show information for video streams
    """
    cmd = 'ffprobe -v quiet -show_format -print_format json -show_streams ' \
          '-select_streams v:0 {0}'.format(input_filename)
    metadata = run_command(
        cmd, error_class=MetadataExtractionExecutionError
    ).decode('utf-8')

    if not metadata:
        raise MetadataExtractionExecutionError(
            'No metadata extracted running {0}, '
            'try to increase verbosity to see the errors')

    return _refactoring_metadata(_patch_aspect_ratio(json.loads(metadata)))


#
# Aspect Ratio  # TODO remove when Sorenson is updated
#
def probe_aspect_ratio(input_filename):
    """Probe video's aspect ratio, calculating it if needed."""
    metadata = ff_probe_all(input_filename)
    return metadata['streams'][0]['display_aspect_ratio']


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
    sinfo = metadata['streams'][0]
    key = 'display_aspect_ratio'
    if sinfo[key] == '0:1':
        sinfo[key] = _calculate_aspect_ratio(sinfo['width'], sinfo['height'])
    return metadata


def _go_deep(key, metadata, fun=None):
    fun = fun or (lambda x: x)
    subpaths = key.split('/')
    value = metadata
    key = metadata
    # Scroll down the list / dictionary to the required value
    for subpath in subpaths:
        try:
            # if it's a number, it search for a list
            subpath = int(subpath)
        except ValueError:
            # it's a key of dictionary
            pass
        key = value
        value = value[subpath]
    # set a new value if required (default leave as it is)
    key[subpath] = fun(value)
    # return the value as output
    return key[subpath]


def _extract_first_found(keys, metadata, fun=None):
    """Extract first metadata found."""
    for key in keys:
        try:
            return _go_deep(key=key, metadata=metadata, fun=fun)
        except KeyError:
            pass
    # if the value is not found, return a default value
    return ''


def _refactoring_metadata(metadata):
    """Refactoring metadata."""
    for key, aliases in app.config['CDS_FFMPEG_METADATA_ALIASES'].items():
        key_base = key.split('/')
        key_last = key_base.pop()

        def set_value(x):
            """Set new value."""
            x[key_last] = value
            return x

        try:
            value = _extract_first_found(keys=aliases, metadata=metadata)
            if value:
                _go_deep(key='/'.join(key_base), metadata=metadata,
                         fun=set_value)
        except KeyError:
            pass

    def split_and_trim(value_string):
        """Split and trim value."""
        return [value.strip() for value in value_string.split(',')]
    for key in app.config['CDS_FFMPEG_METADATA_POST_SPLIT']:
        try:
            _go_deep(key=key, metadata=metadata, fun=split_and_trim)
        except KeyError:
            pass
    return metadata


#
# Frame extraction
#
def ff_frames(input_file, start, end, step, duration, output,
              progress_callback=None):
    """Extract requested frames from video.

    :param input_file: the input video file
    :param start: time position to begin extracting frames
    :param end: time position to stop extracting frames
    :param step: time interval between frames
    :param duration: the total duration of the video
    :param output: output folder and format for the file names as in Python
    string templates (i.e /path/to/somewhere/frames-{:02d}.jpg)
    :param progress_callback: function taking as parameter the index of the
    currently processed frame
    :raises subprocess.CalledProcessError: if any error occurs in the execution
    of the ``ffmpeg`` command
    """
    # Check the validity of the arguments
    if not all([0 < start < duration, 0 < end < duration, 0 < step < duration,
                start < end, (end - start) % step < 0.05]):
        raise FrameExtractionInvalidArguments()

    # Iterate over requested timestamps
    timestamps = takewhile(lambda t: t <= end, count(start, step))
    for i, timestamp in enumerate(timestamps):
        # Construct ffmpeg command
        cmd = 'ffmpeg -accurate_seek -ss {0} -i {1} -vframes 1 {2}'.format(
            timestamp, input_file, output.format(i + 1))

        # Run ffmpeg command
        run_command(cmd, error_class=FrameExtractionExecutionError)

        # Report progress
        if progress_callback:
            progress_callback(i + 1)


#
# Subprocess wrapper
#
def run_command(command, error_class=FFmpegExecutionError, **kwargs):
    """Run ffmpeg command and capture errors."""
    kwargs.setdefault('stderr', STDOUT)
    try:
        return check_output(command.split(), **kwargs)
    except CalledProcessError as e:
        raise error_class(e)
