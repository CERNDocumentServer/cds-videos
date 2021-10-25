# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2021 CERN.
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

"""Opencast utils."""
from flask import current_app


def get_qualities(video_height=None, video_width=None):
    """Return the qualities given the video's height and width.

    :param video_height: maximum output height for transcoded video
    :param video_width: maximum output width for transcoded video
    :returns the qualities
    """
    qualities = []
    for preset in current_app.config['CDS_OPENCAST_QUALITIES'].items():
        if (video_height and video_height >= preset[1]['height']) or \
                (video_width and video_width >= preset[1]['width']):
            qualities.append(preset[0])
    if not qualities:
        qualities.append(
            current_app.config['CDS_OPENCAST_QUALITIES'].items()[0][0]
        )
    return qualities
