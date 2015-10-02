# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Image MARC 21 field definitions."""

from cds.base.dojson.marc21.translations.image import translation as marc21

from dojson import utils


@marc21.over('album_parent', '^774[10_][8_]', override=True)
@utils.for_each_value
def album_parent(self, key, value):
    """Album ID which contains this photo"""
    return {
        'dump_album': value.get('a'),
        'album_id': value.get('r')
    }


@marc21.over('image_url', '^856.[10_28]', override=True)
@utils.for_each_value
@utils.filter_values
def image_url(self, key, value):
    """Image URL. Contains the URL to the concrete image file
    and information about the format
    """
    indicator1_map = {"4": "http", "7": "method_in_subfield"}
    return {
        'size': value.get('s'),
        'path': value.get('d'),
        'electronic_format_type': value.get('q'),
        'uri': value.get('u'),
        'link_text': value.get('y'),
        'public_note': value.get('z'),
        'subformat': value.get('x'),
        'photo_id': value.get('8'),
        'access_method_subfield': value.get('2'),
        'access_method': indicator1_map.get(key[3]),
    }
