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

from ..model import to_cds_json, to_cds_marc21


@to_cds_json.over('french_summary_note', '^590__')
@utils.for_each_value
@utils.filter_values
def french_summary_note(self, key, value):
    """French summary note."""
    return {
        'smuary': value.get('a'),
        'expansion_of_summary_note': value.get('b')
    }


@to_cds_marc21.over('590', 'french_summary_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_french_summary_note(self, key, value):
    """French summary note."""
    return {
        'a': value.get('smuary'),
        'b': value.get('expansion_of_summary_note'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('field_591', '^591__')
@utils.for_each_value
@utils.filter_values
def field_591(self, key, value):
    """Type of Document."""
    return {
        'subfield_a': value.get('a'),
        'subfield_b': value.get('b')
    }


@to_cds_marc21.over('591', 'field_591')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_field_591(self, key, value):
    """Type of Document."""
    return {
        'a': value.get('subfield_a'),
        'b': value.get('subfield_b'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('type_of_document', '^594__')
@utils.for_each_value
def type_of_document(self, key, value):
    """Type of Document."""
    return value.get('a')


@to_cds_marc21.over('594', 'type_of_document')
@utils.reverse_for_each_value
def reverse_type_of_document(self, key, value):
    """Type of Document."""
    return {
        'a': value.get('type_of_document'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('internal_note', '^595__')
@utils.for_each_value
@utils.filter_values
def internal_note(self, key, value):
    """Internal NOTE."""
    return {
        'internal_note': value.get('a'),
        'control_field': value.get('d'),
        'inspect_number': value.get('i'),
        'subject_note': value.get('s'),
        'dump': value.get('9')
    }


@to_cds_marc21.over('595', 'internal_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_internal_note(self, key, value):
    """Reverse - Internal note - text for use internally for debug purposes"""
    return {
        'a': value.get('internal_note'),
        'd': value.get('control_field'),
        'i': value.get('inspect_number'),
        's': value.get('subject_note'),
        '9': value.get('dump'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('slac_note', '^596.')
@utils.for_each_value
@utils.filter_values
def slac_note(self, key, value):
    """Slac note - some kind of internal note"""
    return {
        'slac_note': value.get('a'),
        'dump': value.get('b'),
    }


@to_cds_marc21.over('596', 'slac_note')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_slac_note(self, key, value):
    """Reverse - Slac note - some kind of internal note"""
    return {
        'a': value.get('slac_note'),
        'b': value.get('dump'),
        '$ind1': '_',
        '$ind2': '_',
    }
