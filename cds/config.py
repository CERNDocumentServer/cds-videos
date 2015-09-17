# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""CDS Configuration.

Instance independent configuration (e.g. which extensions to load) is defined
in ``cds.config'' while instance dependent configuration (e.g. database
host etc.) is defined in an optional ``cds.instance_config'' which
can be installed by a separate package.

This config module is loaded by the Flask application factory via an entry
point specified in the setup.py::

    entry_points={
        'invenio.config': [
            "cds = cds.config"
        ]
    },
"""

from __future__ import unicode_literals

from collections import MutableSequence

from invenio_base.config import PACKAGES as _PACKAGES
from invenio_records.config import (
    RECORD_KEY_ALIASES as _RECORD_KEY_ALIASES,
    RECORD_PROCESSORS as _RECORD_PROCESSORS
)


def _concat_fields_into_list(*args):
    """Helper functions to concatenate fields into one list."""
    def concat_field_into_list(self, key):
        values = []
        for k in args:
            value = self.get(k)
            if value is None:
                continue
            if not isinstance(value, MutableSequence):
                values.append(value)
            else:
                values.extend(value)
        return values
    return concat_field_into_list

PACKAGES = [
    "cds.base",
    "cds.modules.personal_collection",
] + _PACKAGES

EXTENSIONS = [
    'invenio.ext.confighacks',
    'invenio.ext.passlib:Passlib',
    'invenio.ext.debug_toolbar',
    'invenio.ext.babel',
    'invenio.ext.sqlalchemy',
    'invenio.ext.sslify',
    'invenio.ext.cache',
    'invenio.ext.session',
    'invenio.ext.login',
    'invenio.ext.principal',
    'invenio.ext.email',
    'invenio.ext.fixtures',
    'invenio.ext.mixer',
    'invenio.ext.legacy',
    'invenio.ext.assets',
    'invenio.ext.template',
    'invenio.ext.admin',
    'invenio.ext.logging',
    'invenio.ext.logging.backends.fs',
    'invenio.ext.logging.backends.legacy',
    'invenio.ext.logging.backends.sentry',
    'invenio.ext.gravatar',
    'invenio.ext.collect',
    'invenio.ext.restful',
    'invenio.ext.menu',
    'invenio.ext.jasmine',  # after assets
    'flask.ext.breadcrumbs:Breadcrumbs',
    'invenio_deposit.url_converters',
    'invenio.ext.es',
]


CFG_SITE_NAME = "CERN Document Server"
CFG_SITE_NAME_INTL = {
    "en": "CDS",  # Shouldn't be required.
    "fr": "CDS",
    "de": "CDS",
    "it": "CDS"
}

CFG_SITE_MISSION = "Access articles, reports and multimedia content in HEP"
CFG_SITE_MISSION_INTL = dict(
    en="Access articles, reports and multimedia content in HEP",
    fr="Articles, rapports et multimédia de la physique des hautes énergies",
)

CFG_SITE_LANGS = ["en", "fr", "de", "it"]

# Invenio Records configuration
RECORD_PROCESSORS = dict()
RECORD_PROCESSORS.update(_RECORD_PROCESSORS)
RECORD_PROCESSORS['marcxml'] = 'cds.base.dojson.cds_marc21.convert_cdsmarcxml'

# Records aliases
RECORD_KEY_ALIASES = dict()
RECORD_KEY_ALIASES.update(_RECORD_KEY_ALIASES)
RECORD_KEY_ALIASES['title'] = _concat_fields_into_list(
    'translation_of_title_by_cataloging_agency',
    'title_statement',
    'varying_form_of_title',
    'edition_statement',
    'abbreviated_title',
    'key_title',
    'main_entry_meeting_name.'
    'meeting_name_or_jurisdiction_name_as_entry_element',
    'added_entry_meeting_name.'
    'meeting_name_or_jurisdiction_name_as_entry_element',
)
RECORD_KEY_ALIASES['author'] = _concat_fields_into_list(
    'main_entry_personal_name',
    'added_entry_personal_name',
    'translator.personal_name',
)
RECORD_KEY_ALIASES['abstract'] = _concat_fields_into_list(
    'summary',
    'french_summary_note',
)
RECORD_KEY_ALIASES['keywords'] = _concat_fields_into_list(
    'index_term_uncontrolled',
    'thesaurus_terms',
)
RECORD_KEY_ALIASES['reportnumber'] = _concat_fields_into_list(
    'file_number',
    'report_number.report_number',
    'report_number._report_number',
    'source_of_acquisition.stock_number',
    'international_standard_number',
    'immediate_source_of_acquisition_note.accession_number',
)
RECORD_KEY_ALIASES['subject'] = 'subject_added_entry_topical_term'
# TODO: References 999C5 $* [many subfields]
RECORD_KEY_ALIASES['division'] = _concat_fields_into_list(
    'added_entry_corporate_name.cern_work',
    'added_entry_corporate_name.institution_to_which_field_applies',
)
RECORD_KEY_ALIASES['year'] = _concat_fields_into_list(
    'dissertation_note.name_of_granting_institution',
    'publication_distribution_imprint.date_of_publication_distribution',
    'dates.opening',
)
RECORD_KEY_ALIASES['series'] = 'series_statement'
RECORD_KEY_ALIASES['experiment'] = 'accelerator_experiment.experiment'
RECORD_KEY_ALIASES['indicator'] = 'subject_indicator'  # TODO: 697C_a
RECORD_KEY_ALIASES['accelerator'] = 'accelerator_experiment.accelerator'
RECORD_KEY_ALIASES['sysno'] = 'sysno.sysno'
RECORD_KEY_ALIASES['disp'] = 'status_week.display_period_for_books'
RECORD_KEY_ALIASES['sysnos'] = _concat_fields_into_list(
    'sysno.sysno',
    'system_control_number.system_control_number',
)
RECORD_KEY_ALIASES['collaboration'] = \
        'added_entry_corporate_name.miscellaneous_information'
RECORD_KEY_ALIASES['global_base'] = 'cata.library'
RECORD_KEY_ALIASES['product'] = 'subject_indicator'
RECORD_KEY_ALIASES['use'] = 'internal_note'
RECORD_KEY_ALIASES['media'] = 'physical_medium.material_base_and_configuration'
RECORD_KEY_ALIASES['restrictions'] = 'restrictions_on_access_note'
RECORD_KEY_ALIASES['funding_project_number'] = \
        'funding_information_note.project_number'

CFG_ACCESS_CONTROL_NOTIFY_USER_ABOUT_NEW_ACCOUNT = 0

BLOCK_GOOGLE_TRANSLATE = False

try:
    from cds.instance_config import *  # noqa
except ImportError:
    pass
