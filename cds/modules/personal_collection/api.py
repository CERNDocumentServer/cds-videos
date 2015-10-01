# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Personal collections API."""

from invenio_ext.cache import cache

from .models import PersonalCollectionSettings
from .registry import boxes


def get_available_box_types():
    """Return dictionary with the available box types.

    The value in the dictionary is a tuple containing the box display name and
    the name prefix of the templates to the used.
    .. code-block:: python

        {
            'record_list': ('Search', 'record_list'),
            'loan_list': ('Loans', 'loan_list'),
            'image': ('Feature Image', 'one_image')
        }
    """
    return {box_name: (box.__display_name__, box.__template__)
            for (box_name, box) in boxes.iteritems()}


def get_boxes_settings(uid, collection='home'):
    """Return the settings for the boxes for the collection page.

    :param uid: User ID to retrieve the box settings.
    :param collection: Collection name, by default `home`
    :returns: Ordered list with the box settings

    """
    return PersonalCollectionSettings.get(uid, collection)


def set_boxes_settings(uid, settings, collection='home'):
    """Update the settings for all the boxes.

    :param uid: User ID to retrieve the box settings.
    :param settings: Settings for all the boxes.
    :param collection: Collection name, by default `home`
    :returns: The saved settings

    """
    cache.delete_memoized(
        create_boxes_content, uid, collection)
    return PersonalCollectionSettings.set(
        uid, settings, collection)


def set_box_settings(uid, index, settings, collection='home'):
    """Update the settings for one box given its order.

    :param uid: User ID to retrieve the box settings.
    :param index: Index of the box in the ordered list
    :param settings: New box configuration
    :param collection: Collection name, by default `home`
    :returns: The saved settings

    """
    cache.delete_memoized(
        create_boxes_content, uid, collection)
    settings = PersonalCollectionSettings.get(
        uid, collection)
    settings[index] = settings
    return PersonalCollectionSettings.set(
        uid, settings, collection)[index]


def delete_box(uid, index, collection='home'):
    """Delete the box given its index.

    :param uid: User ID to retrieve the box settings.
    :param index: Box index inside the ordered list
    :param collection: Collection name, by default `home`
    :returns: TODO

    """
    cache.delete_memoized(
        create_boxes_content, uid, collection)
    settings = get_boxes_settings(uid, collection)
    del settings[index]
    return PersonalCollectionSettings.set(
        uid, settings, collection)


@cache.memoize(timeout=300)
def create_boxes_content(uid, collection='home'):
    """Create the content of all the boxes.

    :param uid: User ID to retrieve the box settings.
    :param collection: Collection name, by default `home`
    :returns: Ordered list with the content of each box

    """
    boxes_content = []
    all_settings = get_boxes_settings(uid, collection)
    for box_settings in all_settings:
        box = boxes[box_settings['type']](**box_settings)
        boxes_content.append(box.build())
    return boxes_content


def update_box_content(uid, index, collection='home'):
    """Update the content for one box bypassing the cache.

    :param uid: User ID to retrieve the box settings.
    :param index: Box index inside the ordered list
    :param collection: Collection name, by default `home`
    :returns: `dict` with the content of the box

    """
    cache.delete_memoized(
        create_boxes_content, uid, collection)
    box_settings = get_boxes_settings(uid, collection)[index]
    box = boxes[box_settings['type']](**box_settings)
    return box.build()
