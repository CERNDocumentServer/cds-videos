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


@to_cds_json.over('added_entry_corporate_name', '^710[10_2][_2]', override=True)
@utils.for_each_value
@utils.filter_values
def added_entry_corporate_name(self, key, value):
    """Added Entry-Corporate Name."""
    indicator_map1 = {
        "0": "Inverted name",
        "1": "Jurisdiction name",
        "2": "Name in direct order"}
    indicator_map2 = {"#": "No information provided", "2": "Analytical entry"}
    return {
        'authority_record_control_number': utils.force_list(
            value.get('0')
        ),
        'materials_specified': value.get('3'),
        'institution_to_which_field_applies': value.get('5'),
        'relator_code': utils.force_list(
            value.get('4')
        ),
        'linkage': value.get('6'),
        'field_link_and_sequence_number': utils.force_list(
            value.get('8')
        ),
        'corporate_name_or_jurisdiction_name_as_entry_element': value.get('a'),
        'location_of_meeting': value.get('c'),
        'subordinate_unit': utils.force_list(
            value.get('b')
        ),
        'relator_term': utils.force_list(
            value.get('e')
        ),
        'date_of_meeting_or_treaty_signing': utils.force_list(
            value.get('d')
        ),
        'miscellaneous_information': value.get('g'),
        'date_of_a_work': value.get('f'),
        'relationship_information': utils.force_list(
            value.get('i')
        ),
        'medium': value.get('h'),
        'form_subheading': utils.force_list(
            value.get('k')
        ),
        'medium_of_performance_for_music': utils.force_list(
            value.get('m')
        ),
        'language_of_a_work': value.get('l'),
        'arranged_statement_for_music': value.get('o'),
        'number_of_part_section_meeting': utils.force_list(
            value.get('n')
        ),
        'name_of_part_section_of_a_work': utils.force_list(
            value.get('p')
        ),
        'version': value.get('s'),
        'key_for_music': value.get('r'),
        'affiliation': value.get('u'),
        'title_of_a_work': value.get('t'),
        'cern_work': value.get('9'),
        'international_standard_serial_number': value.get('x'),
        'type_of_corporate_name_entry_element': indicator_map1.get(key[3]),
        'type_of_added_entry': indicator_map2.get(key[4]),
    }


@to_cds_marc21.over('^710[10_2][_2]', 'added_entry_corporate_name', override=True)
@utils.reverse_for_each_value
@utils.filter_values
def reverse_added_entry_corporate_name(self, key, value):
    """Added Entry-Corporate Name."""
    indicator_map1 = {
        "Inverted name": "0",
        "Jurisdiction name": "1",
        "Name in direct order": "2",
    }
    indicator_map2 = {
        "No information provided": "#",
        "Analytical entry": "2",
    }
    return {
        '0': utils.reverse_force_list(
            value.get('authority_record_control_number')
        ),
        '3': value.get('materials_specified'),
        '5': value.get('institution_to_which_field_applies'),
        '4': utils.reverse_force_list(
            value.get('relator_code')
        ),
        '6': value.get('linkage'),
        '8': utils.reverse_force_list(
            value.get('field_link_and_sequence_number')
        ),
        'a': value.get('corporate_name_or_jurisdiction_name_as_entry_element'),
        'c': value.get('location_of_meeting'),
        'b': utils.reverse_force_list(
            value.get('subordinate_unit')
        ),
        'e': utils.reverse_force_list(
            value.get('relator_term')
        ),
        'd': utils.reverse_force_list(
            value.get('date_of_meeting_or_treaty_signing')
        ),
        'g': value.get('miscellaneous_information'),
        'f': value.get('date_of_a_work'),
        'i': utils.reverse_force_list(
            value.get('relationship_information')
        ),
        'h': value.get('medium'),
        'k': utils.reverse_force_list(
            value.get('form_subheading')
        ),
        'm': utils.reverse_force_list(
            value.get('medium_of_performance_for_music')
        ),
        'l': value.get('language_of_a_work'),
        'o': value.get('arranged_statement_for_music'),
        'n': utils.reverse_force_list(
            value.get('number_of_part_section_meeting')
        ),
        'p': utils.reverse_force_list(
            value.get('name_of_part_section_of_a_work')
        ),
        's': value.get('version'),
        'r': value.get('key_for_music'),
        'u': value.get('affiliation'),
        't': value.get('title_of_a_work'),
        '9': value.get('cern_work'),
        'x': value.get('international_standard_serial_number'),
        '_indicator1': indicator_map1.get('type_of_corporate_name_entry_element'),
        '_indicator2': indicator_map2.get('type_of_added_entry'),
    }

@to_cds_json.over('translator', '^721__')
@utils.for_each_value
@utils.filter_values
def translator(self, key, value):
    """Translator."""
    return {
        'personal_name': value.get('a'),
        'words_translated': value.get('1'),
    }


@to_cds_marc21.over('^721__', 'translator')
@utils.reverse_for_each_value
@utils.filter_values
def reverse_translator(self, key, value):
    """Translator."""
    return {
        'a': value.get('personal_name'),
        '1': value.get('words_translated'),
    }
