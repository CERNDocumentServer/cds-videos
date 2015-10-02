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

from cds.base.dojson.marc21.translations.default import translation as marc21

from dojson import utils


@marc21.over('french_summary_note', '^590__')
@utils.for_each_value
@utils.filter_values
def french_summary_note(self, key, value):
    """French summary note."""
    return {
        'smuary': value.get('a'),
        'expansion_of_summary_note': value.get('b')
    }


@marc21.over('field_591', '^591__')
@utils.for_each_value
@utils.filter_values
def field_591(self, key, value):
    """Type of Document."""
    return {
        'subfield_a': value.get('a'),
        'subfield_b': value.get('b')
    }


@marc21.over('type_of_document', '^594__')
@utils.for_each_value
def type_of_document(self, key, value):
    """Type of Document."""
    return value.get('a')


@marc21.over('internal_note', '^595__')
@utils.for_each_value
@utils.filter_values
def internal_note(self, key, value):
    """Internal NOTE."""
    return {
        'internal_note': value.get('a'),
        'control_field': value.get('d'),
        'inspec_number': value.get('i'),
        'subject_note': value.get('s'),
        'additional_note': value.get('9')
    }


@marc21.over('slac_note', '^596.')
@utils.for_each_value
@utils.filter_values
def slac_note(self, key, value):
    """Slac note - some kind of internal note"""
    return {
        'slac_note': value.get('a'),
        'dump': value.get('b'),
    }
