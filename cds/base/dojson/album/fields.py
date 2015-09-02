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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Album MARC 21 field definitions."""
from dojson import utils

from model import album_to_json, album_to_marc21


@album_to_json.over('photos', '^774..', override=True)
@utils.for_each_value
@utils.filter_values
def photos(self, key, value):
    """Photos in this album"""
    reference = None
    if value.get('r'):
        reference = 'http://cds'r'.cern.ch/record/' + value['r']
    return {
        '$ref': reference,
        'record_type': value.get('a'),
        'cover': value.get('n')
    }  # TODO


@album_to_marc21.over('774', 'photos', override=True)
@utils.reverse_for_each_value
@utils.filter_values
def reverse_photos(self, key, value):
    """Reverse - Photos in this album"""
    reference = None
    if value.get('$ref'):
        reference = value.get('$ref').split('/')[-1]
    return {
        'r': reference,
        'a': value.get('record_type'),
        'n': value.get('cover')
    }
