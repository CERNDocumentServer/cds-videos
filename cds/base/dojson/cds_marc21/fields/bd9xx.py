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

from cds.base.dojson import utils as cds_utils
from dojson import utils

from ..model import cds_marc21


@cds_marc21.over('affiliation_at_conversion', '^901__')
@utils.for_each_value
def affiliation_at_conversion(self, key, value):
    """Affiliation at conversion."""
    return {
        'name_of_institute': value.get('u'),
    }


@cds_marc21.over('grey_book', '^903__')
@utils.for_each_value
@utils.filter_values
def grey_book(self, key, value):
    """Grey book."""
    return {
        'approval': value.get('a'),
        'beam': value.get('b'),
        'status_date': value.get('d'),
        'status': value.get('s'),
    }


@cds_marc21.over('approval_status_history', '^9031_')
@utils.for_each_value
@utils.filter_values
def approval_status_history(self, key, value):
    """Approval status history."""
    return {
        'description': value.get('a'),
        'report_number': value.get('b'),
        'category': value.get('c'),
        'date': value.get('d'),
        'deadline': value.get('e'),
        'e-mail': value.get('f'),
        'status': value.get('s'),
    }


@cds_marc21.over('spokesman', '^905__')
@utils.for_each_value
@utils.filter_values
def spokesman(self, key, value):
    """Spokesman."""
    return {
        'address': value.get('a'),
        'telephone': value.get('k'),
        'fax': value.get('l'),
        'e-mail': value.get('m'),
        'personal_name': value.get('p'),
        'private_address': value.get('q'),
    }


@cds_marc21.over('referee', '^906__')
@utils.for_each_value
@utils.filter_values
def referee(self, key, value):
    """Referee."""
    return {
        'address': value.get('a'),
        'telephone': value.get('k'),
        'fax': value.get('l'),
        'e-mail': value.get('m'),
        'personal_name': value.get('p'),
        'private_address': value.get('q'),
        'affiliation': value.get('u'),
    }


@cds_marc21.over('fsgo', '^910__')
@utils.for_each_value
@utils.filter_values
def fsgo(self, key, value):
    """FSGO."""
    return {
        'personal_name': value.get('f'),
        'alternate_abbreviated_title': value.get('9'),
    }


@cds_marc21.over('citation', '^913__')
@utils.for_each_value
@utils.filter_values
def citation(self, key, value):
    """Citation."""
    return {
        'citation': value.get('c'),
        'unformatted_reference': value.get('p'),
        'title_abbreviation': value.get('t'),
        'uniform_resource_identifier': value.get('u'),
        'volume': value.get('v'),
        'year': value.get('y'),
    }


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


@cds_marc21.over('base', '^960__')
@utils.for_each_value
def base(self, key, value):
    """Base."""
    return value.get('a')


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


@cds_marc21.over('aleph_linking_field', '^962__')
@utils.for_each_value
@utils.filter_values
def aleph_linking_field(self, key, value):
    """ALEPH linking field."""
    return {
        'link_type': value.get('a'),
        'sysno': value.get('b'),
        'library': value.get('l'),
        'down_record_link_note': value.get('ln'),
        'up_record_link_note': value.get('m'),
        'year_link': value.get('y'),
        'volume_link': value.get('v'),
        'part_link': value.get('p'),
        'issue_link': value.get('i'),
        'pages_link': value.get('k'),
        'base': value.get('t'),
    }


# We are squashing this field, because it might contain duplicates
# (even though it shouldn't) and we don't want to lose data
@cds_marc21.over('owner', '^963__')
@cds_utils.for_each_squash
@utils.filter_values
def owner(self, key, value):
    """Owner."""
    return {
        'owner': value.get('a'),
        'status': value.get('b')
    }


@cds_marc21.over('item', '^964__')
def item(self, key, value):
    """Item."""
    return {
        'owner': value.get('a'),
    }


# We are squashing this field, because it might contain duplicates
# (even though it shouldn't) and we don't want to lose data
@cds_marc21.over('sysno', '^970__')
@cds_utils.for_each_squash
@utils.filter_values
def sysno(self, key, value):
    """System number taken from AL500 SYS."""
    return {
        'sysno': value.get('a'),
        'surviver': value.get('d'),
    }


@cds_marc21.over('system_number_of_deleted_double_records', '^981__')
@utils.for_each_value
def system_number_of_deleted_double_records(self, key, value):
    """System number of deleted double records."""
    return value.get('a')


@cds_marc21.over('additional_subject_added_entry_topical_term', '^993__')
@utils.for_each_value
@utils.filter_values
def additional_subject_added_entry_topical_term(self, key, value):
    """Additional subject added entry- topical term."""
    return {
        'processes': value.get('q'),
        'accelerator_physics': value.get('r'),
        'technology': value.get('t'),
    }


@cds_marc21.over('references', '^999C5')
@utils.for_each_value
@utils.filter_values
def references(self, key, value):
    """References."""
    return {
        'doi': value.get('a'),
        'authors': value.get('h'),
        'miscellaneous': utils.force_list(
            value.get('m')
        ),
        'issue_number': value.get('n'),
        'order_number': value.get('o'),
        'page': value.get('p'),
        'report_number': value.get('r'),
        'journal_publication_note': value.get('s'),
        'journal_title_abbreviation': value.get('t'),
        'uniform_resource_identifier': value.get('u'),
        'volume': value.get('v'),
        'year': value.get('y'),
    }


@cds_marc21.over('refextract_references', '^999C6')
@utils.for_each_value
def refexctract_references(self, key, value):
    """Refextract references."""
    return {
        'refextract_info': value.get('a'),
    }
