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
from cds.base.dojson.photo.model import photo_to_json, photo_to_marc21


@photo_to_json.over('album', '^774..', override=True)
@utils.for_each_value
def album(self, key, value):
    """Album ID which contains this photo"""
    return {
        'dump_album': value.get('a'),
        'album_id': value.get('r')
    }


@photo_to_marc21.over('774', 'album', override=True)
@utils.reverse_for_each_value
def reverse_album(self, key, value):
    """Reverse - Album ID which contains this photo"""
    return {
        'a': value.get('dump_album'),
        'r': value.get('album_id'),
        '$ind1': '_',
        '$ind2': '_',
    }


@photo_to_json.over('image', '^856.[10_28]', override=True)
@utils.for_each_value
@utils.filter_values
def image(self, key, value):
    """Image. Contains url to the concrete image file
    and information about the format
    """
    indicator_map1 = {"4": "http", "7": "method_in_subfield"}
    return {
        'photo_id': value.get('s'),
        'path': value.get('d'),
        'electronic_format_type': value.get('q'),
        'uri': value.get('u'),
        'link_text': value.get('y'),
        'public_note': value.get('z'),
        'subformat': value.get('x'),
        'sequence_number': value.get('8'),
        'access_method_subfield': value.get('2'),
        'access_method': indicator_map1.get(key[3]),
    }


@photo_to_marc21.over('856', 'image', override=True)
@utils.reverse_for_each_value
@utils.filter_values
def reverse_image(self, key, value):
    """Reverse - Image. Contains url to the concrete
    image file and information about the format
    """
    indicator_map1 = {
        "http": "4",
        "method_in_subfield": "7",
    }
    return {
        's': value.get('photo_id'),
        'd': value.get('path'),
        'q': value.get('electronic_format_type'),
        'u': value.get('uri'),
        'y': value.get('link_text'),
        'z': value.get('public_note'),
        'x': value.get('subformat'),
        '8': value.get('sequence_number'),
        '2': value.get('access_method_subfield'),
        '$ind1': indicator_map1.get(value.get('access_method')),
        '$ind2': '_'
    }


@photo_to_json.over('owner', '^859..', override=True)
@utils.for_each_value
@utils.filter_values
def owner(self, key, value):
    """Information about the people having write permission over this record"""
    return {
        'contact': value.get('a'),
        'e-mail': value.get('f'),
        'date': value.get('x')
    }




@photo_to_marc21.over('859', 'owner', override=True)
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
        '$ind1': '_',
        '$ind2': '_',
    }


@photo_to_marc21.over('^970', 'dump_system_number')
@utils.filter_values
def reverse_system_number(self, key, value):
    """Reverse - System number"""
    return {
        'a': value.get('system_number'),
        'd': value.get('recid_of_surviving_record'),
        '$ind1': '_',
        '$ind2': '_',
    }



