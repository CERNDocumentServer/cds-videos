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


@to_cds_json.over('international_standard_number', '^021..')
@utils.for_each_value
def international_standard_number(self, key, value):
    """Report Number."""
    return value.get('a')


@to_cds_marc21.over('021', 'international_standard_number')
@utils.for_each_value
def reverse_international_standard_number(self, key, value):
    """Report Number."""
    return {
        'a': value['international_standard_number'],
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('system_control_number', '^035..', override=True)
@utils.for_each_value
@utils.filter_values
def system_control_number(self, key, value):
    """System Control Number."""
    return {
        'system_control_number': value.get('a'),
        'field_link_and_sequence_number': utils.force_list(
            value.get('8')
        ),
        'canceled_invalid_control_number': utils.force_list(
            value.get('z')
        ),
        'linkage': value.get('6'),
        'inst': value.get('9'),
    }


@to_cds_marc21.over('035', 'system_control_number', override=True)
@utils.for_each_value
@utils.filter_values
def reverse_system_control_number(self, key, value):
    """System Control Number."""
    return {
        'a': value.get('system_control_number'),
        '8': utils.reverse_force_list(value.get('field_link_and_sequence_number')),
        'z': utils.reverse_force_list(value.get('canceled_invalid_control_number')),
        '6': value.get('linkage'),
        '9': value.get('inst'),
        '$ind1': '_',
        '$ind2': '_',
    }


@to_cds_json.over('report_number', '^088..', override=True)
@utils.for_each_value
@utils.filter_values
def report_number(self, key, value):
    """Report Number."""
    return {
        'report_number': value.get('a'),
        'field_link_and_sequence_number': utils.force_list(
            value.get('8')
        ),
        'canceled_invalid_report_number': utils.force_list(
            value.get('z')
        ),
        'linkage': value.get('6'),
        '_report_number': value.get('9'), # not displayed but searchable
    }


@to_cds_marc21.over('088', 'report_number', override=True)
@utils.reverse_for_each_value
@utils.filter_values
def reverse_report_number(self, key, value):
    """Report Number."""
    return {
        'a': value.get('report_number'),
        '8': utils.force_list(
            value.get('field_link_and_sequence_number')
        ),
        'z': utils.force_list(
            value.get('canceled_invalid_report_number')
        ),
        '6': value.get('linkage'),
        '9': value.get('_report_number'),  # not displayed but searchable
        '$ind1': '_',
        '$ind2': '_',
    }
