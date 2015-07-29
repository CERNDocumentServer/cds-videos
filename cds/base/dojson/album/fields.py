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

from model import album_marc21, album_tomarc21


@album_marc21.over('photos', '^774..')
@utils.for_each_value
@utils.filter_values
def photos(self, key, value):
    """Photos in this album"""
    return {
        '$ref': 'http://cds.cern.ch/record/' + value.get('r'),
        'record_type': value.get('a'),
        'cover': value.get('n')
    }  # TODO


@album_marc21.over('dump_cat', '^961..')
@utils.filter_values
def cat(self, key, value):
    """Dump cat"""
    return {
        'cataloguer': value.get('a'),
        'cataloguer_level': value.get('b'),
        'modification_date': value.get('c'),
        'library': value.get('l'),
        'hour': value.get('h'),
        'creation_date': value.get('x')
    }


@album_tomarc21.over('^774..', 'photos')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_photos(self, key, value):
    """Reverse - Photos in this album"""
    return {
        'r': value.get('$ref').split('/')[-1],
        'a': value.get('record_type'),
        'n': value.get('cover')
    }


@album_tomarc21.over('^961..', 'dump_cat')
@utils.filter_values
def reverse_cat(self, key, value):
    """Reverse - Dump cat"""
    return {
        'a': value.get('cataloguer'),
        'b': value.get('cataloguer_level'),
        'c': value.get('modification_date'),
        'l': value.get('library'),
        'h': value.get('hour'),
        'x': value.get('creation_date'),
    }
