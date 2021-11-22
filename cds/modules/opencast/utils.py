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


def find_lowest_quality():
    """Return the lowest quality available."""
    lowest_height = 100000
    lowest_quality = None
    for quality, preset_items in current_app.config[
            'CDS_OPENCAST_QUALITIES'
    ].items():
        if preset_items["height"] < lowest_height:
            lowest_height = preset_items["height"]
            lowest_quality = quality

    return lowest_quality


def get_qualities(video_height=None, video_width=None):
    """Return the qualities given the video's height and width.

    :param video_height: maximum output height for transcoded video
    :param video_width: maximum output width for transcoded video
    :returns the qualities
    """
    qualities = []
    for quality, preset_items in current_app.config[
        'CDS_OPENCAST_QUALITIES'
    ].items():
        if (video_height and video_height >= preset_items['height']) or \
                (video_width and video_width >= preset_items['width']):
            qualities.append(quality)
    if not qualities:
        lowest_quality = find_lowest_quality()
        qualities.append(lowest_quality)
    return qualities


def can_be_transcoded(subformat_desired_quality, video_width, video_height):
    """Return the details of the subformat that will be generated.

    :param subformat_desired_quality: the quality desired for the subformat
    :param video_width: the original video width
    :param video_height: the original video height
    :returns a dict with width and height if the subformat can
    be generated, or False otherwise
    """
    try:
        qualitiy_config = current_app.config[
            'CDS_OPENCAST_QUALITIES'
        ][subformat_desired_quality]
    except KeyError:
        return None

    if video_height < qualitiy_config[
        'height'
    ] or video_width < qualitiy_config['width']:
        return None

    return dict(
        preset_quality=subformat_desired_quality,
        width=qualitiy_config['width'],
        height=qualitiy_config['height']
    )


def build_subformat_key(preset_quality):
    """Build the object version key connected with the transcoding."""
    return '{0}.mp4'.format(preset_quality)
