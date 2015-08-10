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

"""CDS special/custom tags."""

from dojson import utils
from cds.base.dojson.utils import for_each_squash
from ..model import to_cds_json, to_cds_marc21


@to_cds_json.over('status_week', '^916__')
@utils.for_each_value
@utils.filter_values
def status_week(self, key, value):
    """Status week."""
    return {
        'acquisition_of_proceedings_code': value.get('a'),
        'display_period_for_books': value.get('d'),
        'number_of_copies_bought_by_cern': value.get('e'),
        'status_of_record': value.get('s'),
        'status_week': value.get('w'),
        'year_for_annual_list': value.get('y'),
    }

@to_cds_marc21.over('916', 'status_week')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_status_week(self, key, value):
    """Reverse - Record type - mostly IMAGE"""
    return {
        'a': value.get('acquisition_of_proceedings_code'),
        'd': value.get('display_period_for_books'),
        'e': value.get('number_of_copies_bought_by_cern'),
        's': value.get('status_of_record'),
        'w': value.get('status_week'),
        'y': value.get('year_for_annual_list'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('place_of_photo', '^923..')
@utils.for_each_value
@utils.filter_values
def place_of_photo(self, key, value):
    """Place of photo where it was taken and requester info"""
    return {
        'place': value.get('p'),
        'requester': value.get('r')
    }

@to_cds_marc21.over('923', 'place_of_photo')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_place_of_photo(self, key, value):
    """Reverse - Place of photo where it was taken and requester info"""
    return {
        'p': value.get('place'),
        'r': value.get('requester'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('photolab', '^924..')
@utils.for_each_value
@utils.filter_values
def photolab(self, key, value):
    """Photolab"""
    return {
        'tirage': value.get('a'),
        'photolab_1': value.get('b'),
        'photolab_2': value.get('t'),
    }


@to_cds_marc21.over('924', 'photolab')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_photolab(self, key, value):
    """Photolab"""
    return {
        'a': value.get('tirage'),
        'b': value.get('photolab_1'),
        't': value.get('photolab_2'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('dates', '^925__')
@utils.for_each_value
@utils.filter_values
def dates(self, key, value):
    """Dates."""
    return {
        'opening': value.get('a'),
        'closing': value.get('b')
    }


@to_cds_marc21.over('925', 'dates')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_dates(self, key, value):
    """Dates."""
    return {
        'a': value.get('opening'),
        'b': value.get('closing'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('file_number', '^927__')
@utils.for_each_value
def file_number(self, key, value):
    """File Number."""
    return value.get('a')


@to_cds_marc21.over('927' 'file_number')
@utils.reverse_for_each_value
def reverse_file_number(self, key, value):
    """File Number."""
    return {
        'a': value.get('file_number'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('base', '^960__')
@utils.for_each_value
def base(self, key, value):
    """Base."""
    return value.get('a')


@to_cds_marc21.over('960', 'base')
@utils.reverse_for_each_value
def base(self, key, value):
    """Base."""
    return {
        'a': value,
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('peri_internal_note', '^937__')
@utils.for_each_value
@utils.filter_values
def peri_internal_note(self, key, value):
    """Peri: internal note."""
    return {
        'internal_note': value.get('a'),
        'modification_date': value.get('c'),
        'responsible_of_the_modification': value.get('s'),
    }


@to_cds_marc21.over('937', 'peri_internal_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_peri_internal_note(self, key, value):
    """Peri: internal note."""
    return {
        'a': value.get('internal_note'),
        'c': value.get('modification_date'),
        's': value.get('responsible_of_the_modification'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('cat', '^961__')
@utils.for_each_value
@utils.filter_values
def cat(self, key, value):
    """CAT."""
    return {
        'cataloger': value.get('a'),
        'cataloger_level': value.get('b'),
        'modification_date': value.get('c'),
        'library': value.get('l'),
        'hour': value.get('h'),
        'creation_date': value.get('x'),
    }


@to_cds_marc21.over('961', 'cat')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_cat(self, key, value):
    """CAT."""
    return {
        'a': value.get('cataloger'),
        'b': value.get('cataloger_level'),
        'c': value.get('modification_date'),
        'l': value.get('library'),
        'h': value.get('hour'),
        'x': value.get('creation_date'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('visibility', '^963..')
@utils.for_each_value
@utils.filter_values
def owner(self, key, value):
    """Owner."""
    return {
        'owner': value.get('a'),
        'status': value.get('b')
    }


@to_cds_marc21.over('963', 'visibility')
@for_each_squash
@utils.filter_values
def reverse_owner(self, key, value):
    """Reverse - Visibility"""
    return {
        'a': value.get('owner'),
        'b': value.get('status'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('sysno', '^970__')
@utils.for_each_value
@utils.filter_values
def sysno(self, key, value):
    """System number taken from AL500 SYS."""
    return {
        'sysno': value.get('a'),
        'surviver': value.get('d'),
    }


@to_cds_marc21.over('970', 'sysno')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_system_number(self, key, value):
    """Reverse - System number"""
    return {
        'a': value.get('sysno'),
        'd': value.get('surviver'),
        '$ind1': '_',
        '$ind2': '_',
    }

@to_cds_json.over('collection', '^980..')
@utils.for_each_value
@utils.filter_values
def collection(self, key, value):
    """Reverse - Collection to which this photo belongs"""
    return {
        'primary': value.get('a'),
        'secondary': value.get('b'),
        'deleted': value.get('c'),
    }


@to_cds_marc21.over('980', 'collection')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_collection(self, key, value):
    """Reverse - Collection to which this photo belongs"""
    return {
        'a': value.get('primary'),
        'b': value.get('secondary'),
        'c': value.get('deleted'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('record_type', '^999..')
@utils.for_each_value
@utils.filter_values
def record_type(self, key, value):
    """Record type - mostly IMAGE"""
    return {
        'record_type': value.get('a'),
        'dump': value.get('9'),
    }


@to_cds_marc21.over('999', 'record_type')
@for_each_squash
@utils.filter_values
def reverse_record_type(self, key, value):
    """Reverse - Record type - mostly IMAGE"""
    return {
        'a': value.get('record_type'),
        '9': value.get('dump'),
        '$ind1': '_',
        '$ind2': '_',
    }
