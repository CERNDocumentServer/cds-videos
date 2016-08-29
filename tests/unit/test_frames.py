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
import av


def test_av():
    """Test frame extraction."""

    # Settings
    percentage = 0.01

    # Extract frames
    container = av.open('/home/orestis/Downloads/test.mp4')
    video_stream = next(s for s in container.streams if s.type == 'video')
    frame_step = video_stream.frames * percentage
    frame_iterator = islice(container.decode(video=0), 0, None, frame_step)
    for i, frame in enumerate(frame_iterator):
        frame.to_image().save('/home/orestis/Downloads/%04d.jpg' % i)

    # Create thumbnails
    # Image.thumbnail()
