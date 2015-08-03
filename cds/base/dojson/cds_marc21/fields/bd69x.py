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


@to_cds_json.over('subject_indicator', '^690C_')
@utils.for_each_value
def subject_indicator(self, key, value):
    """Subject Indicator."""
    return value.get('a')


@to_cds_marc21.over('^690C_', 'subject_indicator')
@utils.reverse_for_each_value
def reverse_indicator(self, key, value):
    """Reverse - Record type"""
    return {
        'a': value,
        '_indicator1': 'C',
        '_indicator2': '_'
    }


@to_cds_json.over('accelerator_experiment', '^693__')
@utils.for_each_value
@utils.filter_values
def accelerator_experiment(self, key, value):
    """Expriment."""
    return {
        'acelerator': value.get('a'),
        'experiment': value.get('e'),
        'facility': value.get('f'),
        'subfield_s': value.get('s'),
    }


@to_cds_marc21.over('^693__', 'accelerator_experiment')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_accelerator_experiment(self, key, value):
    """Expriment."""
    return {
        'a': value.get('acelerator'),
        'e': value.get('experiment'),
        'f': value.get('facility'),
        's': value.get('subfield_s'),
    }


@to_cds_json.over('thesaurus_terms', '^695__')
@utils.for_each_value
@utils.filter_values
def thesaurus_terms(self, key, value):
    """Expriment."""
    return {
        'uncontrolled_term': value.get('a'),
        'institute': value.get('9'),
    }


@to_cds_marc21.over('^695__', 'thesaurus_terms')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_thesaurus_terms(self, key, value):
    """Expriment."""
    return {
        'a': value.get('uncontrolled_term'),
        '9': value.get('institute'),
    }
