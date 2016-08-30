# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Test frame extraction."""

from __future__ import absolute_import, print_function

from subprocess import check_output
from math import ceil, sqrt
from PIL import Image


def test_av():
    """Test frame extraction."""

    #
    # FFmpeg wrappers
    #
    def get_duration(input):
        return float(check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            '{}'.format(input)
        ]))

    def extract_frames(input, time_step, output):
        return check_output([
            'ffmpeg',
            '-i', '{}'.format(input),
            '-vf', 'fps=1/{}'.format(time_step),
            '{}'.format(output)
        ], stderr=None)

    #
    # Settings
    #
    percentage = 0.01
    step = 100

    #
    # Extraction
    #
    input = '/home/orestis/Downloads/test.mp4'
    output = '/home/orestis/Downloads/img%d.jpg'
    duration = get_duration(input)
    time_step = duration * percentage
    image_no = int(duration // time_step)
    extract_frames(input, time_step, output)

    size = int(ceil(sqrt(image_no))) * step
    final_image = Image.new('RGB', (size, size))
    positions = ((i, j)
                 for i in range(0, size, step)
                 for j in range(0, size, step))
    for i in range(1, image_no):
        im = Image.open('/home/orestis/Downloads/img{}.jpg'.format(i))
        im.thumbnail((step, step))
        final_image.paste(im, positions.next())

    final_image.save('/home/orestis/Downloads/test.jpg')
