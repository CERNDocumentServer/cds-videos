# -*- coding: utf-8 -*-
#
# This file is part of DoJSON
# Copyright (C) 2015 CERN.
#
# DoJSON is free software; you can redistribute it and/or
# modify it under the terms of the Revised BSD License; see LICENSE
# file for more details.

"""Photo MARC 21 field definitions."""
from dojson import utils
from utils import for_each_squash
from cds.base.dojson.photo.model import marc21, tomarc21


@marc21.over('imprint', '^269')
@utils.filter_values
def imprint(self, key, value):
    """Caption."""
    return {
        'place_of_publication': value.get('a'),
        'name_of_publisher': value.get('b'),
        'date': value.get('c')
    }


@marc21.over('internal_note', '^595.')
@utils.for_each_value
@utils.filter_values
def internal_note(self, key, value):
    """Internal note - text for use internally for debug purposes"""
    return {
        'internal_note': value.get('a'),
        'control_field': value.get('d'),
        'inspec_number': value.get('i'),
        'subject_note': value.get('s'),
        'dump': value.get('9')
    }


@marc21.over('slac_note', '^596.')
@utils.for_each_value
@utils.filter_values
def slac_note(self, key, value):
    """Slac note - some kind of internal note"""
    return {
        'slac_note': value.get('a')
    }


@marc21.over('indicator', '^690C.')
@utils.for_each_value
def indicator(self, key, value):
    """Record type"""
    return value.get('a')


@marc21.over('album', '^774..')
def album(self, key, value):
    """Album ID which contains this photo"""
    return {
        'dump_album': value.get('a'),
        'album_id': value.get('r')
    }


@marc21.over('image', '^8564.')
@utils.for_each_value
@utils.filter_values
def image(self, key, value):
    """Image. Contains url to the concrete image file
    and information about the format
    """
    return {
        'photo_id': value.get('s'),
        'path': value.get('d'),
        'electronic_format_type': value.get('q'),
        'uri': value.get('u'),
        'link_text': value.get('y'),
        'public_note': value.get('z'),
        'subformat': value.get('x')
    }


@marc21.over('owner', '^859..')
@utils.for_each_value
@utils.filter_values
def owner(self, key, value):
    """Information about the people having write permission over this record"""
    return {
        'contact': value.get('a'),
        'e-mail': value.get('f'),
        'date': value.get('x')
    }


@marc21.over('dump_status_week', '^916..')
@utils.filter_values
def status_week(self, key, value):
    """Record type - mostly IMAGE"""
    return {
        'acquisition_of_proceedings_code': value.get('a'),
        'display_period': value.get('d'),
        'copies_bought': value.get('e'),
        'status_of_record': value.get('s'),
        'status_week': value.get('w'),
        'year': value.get('y')
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


@marc21.over('base_number', '^960..')
def base(self, key, value):
    """Base number"""
    return value.get('a')


@marc21.over('visibility', '^963..')
@for_each_squash
@utils.filter_values
def visibility(self, key, value):
    """Visibility"""
    return {
        'scope': value.get('a'),
        'visibility': value.get('b')
    }


@marc21.over('dump_system_number', '^970..')
def system_number(self, key, value):
    """System number"""
    return {
        'system_number': value.get('a'),
        'recid_of_surviving_record': value.get('d')
    }


@marc21.over('collection', '^980..')
@utils.for_each_value
@utils.filter_values
def collection(self, key, value):
    """Collection to which this photo belongs"""
    return {
        'primary': value.get('a'),
        'secondary': value.get('b')
    }


@marc21.over('record_type', '^999..')
def record_type(self, key, value):
    """Record type - mostly IMAGE"""
    return value.get('a')


@tomarc21.over('^269', 'imprint')
@utils.filter_values
def reverse_imprint(self, key, value):
    """Reverse - Caption."""
    return {
        'a': value.get('place_of_publication'),
        'b': value.get('name_of_publisher'),
        'c': value.get('date')
    }


@tomarc21.over('^595.', 'internal_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_internal_note(self, key, value):
    """Reverse - Internal note - text for use internally for debug purposes"""
    return {
        'a': value.get('internal_note'),
        'd': value.get('control_field'),
        'i': value.get('inspec_number'),
        's': value.get('subject_note'),
        '9': value.get('dump')
    }


@tomarc21.over('^596.', 'slac_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_slac_note(self, key, value):
    """Reverse - Slac note - some kind of internal note"""
    return {
        'a': value.get('slac_note')
    }


@tomarc21.over('^690C.', 'indicator')
@utils.reverse_for_each_value
def reverse_indicator(self, key, value):
    """Reverse - Record type"""
    return {
        'a': value,
        '_indicator1': 'C',
        '_indicator2': '_'
    }


@tomarc21.over('^774..', 'album')
def reverse_album(self, key, value):
    """Reverse - Album ID which contains this photo"""
    return {
        'a': value.get('dump_album'),
        'r': value.get('album_id'),
    }


@tomarc21.over('^8564.', 'image')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_image(self, key, value):
    """Reverse - Image. Contains url to the concrete
    image file and information about the format
    """
    return {
        's': value.get('photo_id'),
        'd': value.get('path'),
        'q': value.get('electronic_format_type'),
        'u': value.get('uri'),
        'y': value.get('link_text'),
        'z': value.get('public_note'),
        'x': value.get('subformat'),
        '_indicator1': '4',
        '_indicator2': '_'
    }


@tomarc21.over('^859..', 'owner')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_owner(self, key, value):
    """Reverse - Information about the people
    having write permission over this record
    """
    return {
        'a': value.get('contact'),
        'f': value.get('e-mail'),
        'x': value.get('date'),
    }


@tomarc21.over('^916..', 'dump_status_week')
@utils.filter_values
def reverse_status_week(self, key, value):
    """Reverse - Record type - mostly IMAGE"""
    return {
        'a': value.get('acquisition_of_proceedings_code'),
        'd': value.get('display_period'),
        'e': value.get('copies_bought'),
        's': value.get('status_of_record'),
        'w': value.get('status_week'),
        'y': value.get('year'),
    }


@tomarc21.over('^923..', 'place_of_photo')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_place_of_photo(self, key, value):
    """Reverse - Place of photo where it was taken and requester info"""
    return {
        'p': value.get('place'),
        'r': value.get('requester'),
    }


@tomarc21.over('^960..', 'base_number')
def reverse_base(self, key, value):
    """Reverse - Base number"""
    return {'a': value}


@tomarc21.over('^963..', 'visibility')
@for_each_squash 
@utils.filter_values
def reverse_visibility(self, key, value):
    """Reverse - Visibility"""
    return {
        'a': value.get('scope'),
        'b': value.get('visibility'),
    }


@tomarc21.over('^970..', 'dump_system_number')
@utils.filter_values
def reverse_system_number(self, key, value):
    """Reverse - System number"""
    return {
        'a': value.get('system_number'),
        'd': value.get('recid_of_surviving_record'),
    }


@tomarc21.over('^980..', 'collection')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_collection(self, key, value):
    """Reverse - Collection to which this photo belongs"""
    return {
        'a': value.get('primary'),
        'b': value.get('secondary'),
    }


@tomarc21.over('^999..', 'record_type')
def reverse_record_type(self, key, value):
    """Reverse - Record type - mostly IMAGE"""
    return {'a': value}
