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
from itertools import islice

from math import ceil, sqrt

import av
from PIL import Image


def test_av():
    """Test frame extraction."""

    # Settings
    percentage = 0.01
    step = 100
    sub_size = (step, step)

    # Extract frames
    container = av.open('/home/orestis/Downloads/test.mp4')
    video_stream = next(s for s in container.streams if s.type == 'video')
    frame_step = video_stream.frames * percentage
    frame_iterator = islice(container.decode(video=0), 0, None, frame_step)
    images = [frame.to_image() for frame in frame_iterator]
    map(lambda im: im.thumbnail(sub_size), images)
    image_no = len(images)
    print('#Images: {}'.format(image_no))

    # Calculate sizes
    size = int(ceil(sqrt(image_no))) * step
    print('Size: {}'.format(size))
    final_size = (size, size)

    # Create thumbnails
    images = iter(images)
    final_image = Image.new('RGB', final_size)
    for i in range(0, size + step, step):
        for j in range(0, size + step, step):
            print(i, j)
            try:
                final_image.paste(images.next(), (i, j))
            except StopIteration:
                break

    final_image.save('/home/orestis/Downloads/test.jpg')
