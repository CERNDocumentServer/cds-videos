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

from ..model import cds_marc21


@cds_marc21.over('international_standard_number', '^021..')
@utils.for_each_value
def international_standard_number(self, key, value):
    """Report Number."""
    return value.get('a')


@cds_marc21.over('system_control_number', '^035..', override=True)
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


@cds_marc21.over('report_number', '^088..', override=True)
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
        '_report_number': value.get('9'),  # not displayed but searchable
    }
