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
from contextlib import contextmanager
from functools import wraps

from flask import current_app
from invenio_cache import current_cache


def find_lowest_quality():
    """Return the lowest quality available."""
    lowest_height = None
    lowest_quality = None
    for quality, preset_items in current_app.config[
        "CDS_OPENCAST_QUALITIES"
    ].items():
        lowest_height = lowest_height or preset_items["height"] + 1
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
        "CDS_OPENCAST_QUALITIES"
    ].items():
        if (video_height and video_height >= preset_items["height"]) or (
            video_width and video_width >= preset_items["width"]
        ):
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
        qualitiy_config = current_app.config["CDS_OPENCAST_QUALITIES"][
            subformat_desired_quality
        ]
    except KeyError:
        return None

    if (
        video_height < qualitiy_config["height"]
        or video_width < qualitiy_config["width"]
    ):
        return None

    return dict(
        preset_quality=subformat_desired_quality,
        width=qualitiy_config["width"],
        height=qualitiy_config["height"],
    )


@contextmanager
def cache_lock(lock_id, timeout):
    """Creates the lock using redis cache and releases it when finished.

    :param lock_id: Lock ID.
    :param timeout: The cache timeout for the key in seconds.
    """
    cache = current_cache.cache
    # if key was already added it will return False
    status = cache.add(lock_id, True, timeout)
    try:
        yield status
    finally:
        if status and cache.has(lock_id):
            current_app.logger.info(
                "Releasing lock with id: {0}".format(lock_id)
            )
            cache.delete(lock_id)


def generate_downloader_lock_id(opencast_event_id):
    """Generates a string used to store it in the cache and use it as a lock."""
    return "downloader_" + opencast_event_id


def _lock_and_run(lock_id, timeout, f, **kwargs):
    """Acquire lock and run passed func."""
    with cache_lock(lock_id, timeout) as acquired:
        if acquired:
            current_app.logger.debug(
                "Acquiring lock with id {0}".format(lock_id)
            )
            f(**kwargs)
        else:
            current_app.logger.debug(
                "Task with lock {0} already running".format(lock_id)
            )


def only_one(key=None, timeout_config_name=None):
    """Decorator to ensure that the function runs only once at a time.

    :param key: The key to identify the unique function.
    :param timeout_config_name: The timeout for releasing the lock.
    """
    def decorator_builder(f):
        @wraps(f)
        def decorate(**kwargs):
            lock_id = key
            assert lock_id
            timeout = current_app.config[timeout_config_name]
            _lock_and_run(lock_id, timeout, f, **kwargs)

        return decorate

    return decorator_builder


def only_one_downloader(timeout_config_name=None):
    """Decorator to ensure that the downloader runs only once at a time.

    :param timeout_config_name: The timeout for releasing the lock.
    """
    def decorator_builder(f):
        @wraps(f)
        def decorate(**kwargs):
            opencast_event_id = kwargs["opencast_event_id"]
            lock_id = generate_downloader_lock_id(opencast_event_id)
            assert lock_id
            timeout = current_app.config[timeout_config_name]
            _lock_and_run(lock_id, timeout, f, **kwargs)

        return decorate

    return decorator_builder

