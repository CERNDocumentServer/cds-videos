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


@cds_marc21.over('status_week', '^916__')
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


@cds_marc21.over('dates', '^925__')
@utils.for_each_value
@utils.filter_values
def dates(self, key, value):
    """Dates."""
    return {
        'opening': value.get('a'),
        'closing': value.get('b')
    }


@cds_marc21.over('file_number', '^927__')
@utils.for_each_value
def file_number(self, key, value):
    """File Number."""
    return value.get('a')


@cds_marc21.over('base', '^960__')
@utils.for_each_value
def base(self, key, value):
    """Base."""
    return value.get('a')


@cds_marc21.over('peri_internal_note', '^937__')
@utils.for_each_value
@utils.filter_values
def peri_internal_note(self, key, value):
    """Peri: internal note."""
    return {
        'internal_note': value.get('a'),
        'modification_date': value.get('c'),
        'responsible_of_the_modification': value.get('s'),
    }


@cds_marc21.over('cat', '^961__')
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


@cds_marc21.over('owner', '^963__')
@utils.for_each_value
@utils.filter_values
def owner(self, key, value):
    """Owner."""
    return {
        'owner': value.get('a'),
        'status': value.get('b')
    }


@cds_marc21.over('sysno', '^970__')
@utils.for_each_value
@utils.filter_values
def sysno(self, key, value):
    """System number taken from AL500 SYS."""
    return {
        'sysno': value.get('a'),
        'surviver': value.get('d'),
    }
