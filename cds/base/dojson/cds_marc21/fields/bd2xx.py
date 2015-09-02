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

@to_cds_json.over('imprint', '^269__')
@utils.for_each_value
@utils.filter_values
def imprint(self, key, value):
    """Pre-publication, distribution, etc.

    NOTE: Don't use the following lines for CER base=14,2n,41-45
    NOTE: Don't use for THESES
    """
    return {
        'place_of_publication': value.get('a'),
        'name_of_publication': value.get('b'),
        'complete_date': value.get('c'),
    }


@to_cds_marc21.over('269', 'imprint')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_imprint(self, key, value):
    """Reverse - Pre-publication, distribution, etc.

    NOTE: Don't use the following lines for CER base=14,2n,41-45
    NOTE: Don't use for THESES
    """
    return {
        'a': value.get('place_of_publication'),
        'b': value.get('name_of_publication'),
        'c': value.get('complete_date'),
        '$ind1': '_',
        '$ind2': '_',
    }
