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

"""Python wrappers for the ffmpeg command-line utility."""

from __future__ import absolute_import

from subprocess import check_output

import pexpect


def ff_probe(input_filename, field):
    """Retrieve requested field from the output of ffprobe."""
    return check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream={}'.format(field),
        '-of', 'default=noprint_wrappers=1:nokey=1',
        '{}'.format(input_filename)
    ]).rstrip()


def ff_probe_all(input_filename):
    """Retrieve requested field from the output of ffprobe."""
    return check_output([
        'ffprobe', '-v', 'error', '-print_format', 'json',
        '-show_format', '-show_streams', '{}'.format(input_filename)
    ]).decode('utf-8')


def ff_frames(input_file, start_time, end_time, time_step, output):
    """Extract requested frames from video, while tracking progress."""
    cmd = 'ffmpeg -i {0} -ss {1} -to {2} -vf fps=1/{3} {4}'.format(
        input_file, start_time, end_time, time_step, output
    )
    thread = pexpect.spawn(cmd)

    regex = thread.compile_pattern_list(
        [pexpect.EOF, 'time=(\d\d:\d\d:\d\d).\d\d']
    )
    while True:
        index = thread.expect_list(regex, timeout=None)
        if index == 0:
            break
        else:
            yield sum(
                int(amount) * 60 ** power for power, amount in
                enumerate(reversed(thread.match.group(1).split(b':')))
            )
