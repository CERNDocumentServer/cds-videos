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

"""CDS Album MARC 21 field definitions."""

from cds.base.dojson.marc21.translations.album import translation as marc21

from dojson import utils


@marc21.over('images', '^774[10_][8_]', override=True)
@utils.for_each_value
@utils.filter_values
def images(self, key, value):
    """Images contained in this album"""
    reference = None
    if value.get('r'):
        reference = 'http://cds.cern.ch/record/' + value['r']
    return {
        '$ref': reference,
        'record_type': value.get('a'),
        'relation': value.get('n')
    }


@marc21.over('place_of_photo', '^923..')
@utils.for_each_value
@utils.filter_values
def place_of_photo(self, key, value):
    """Place of photo where it was taken and requester info"""
    return {
        'place': value.get('p'),
        'requester': value.get('r')
    }


@marc21.over('photolab', '^924..')
@utils.for_each_value
@utils.filter_values
def photolab(self, key, value):
    """Photolab"""
    return {
        'tirage': value.get('a'),
        'photolab_1': value.get('b'),
        'photolab_2': value.get('t'),
    }
