# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS base Invenio configuration."""

from __future__ import absolute_import, print_function

import os

from invenio_records_rest.facets import terms_filter


# Identity function for string extraction
def _(x):
    """Indentity function."""
    return x

###############################################################################
# Translations & Time
###############################################################################

# Default language.
BABEL_DEFAULT_LANGUAGE = 'en'
# Default timezone.
BABEL_DEFAULT_TIMEZONE = 'Europe/Zurich'
# Supported languages.
I18N_LANGUAGES = []

###############################################################################
# Celery
###############################################################################

# RabbitMQ.
BROKER_URL = os.environ.get(
    "APP_BROKER_URL",
    "redis://localhost:6379/0")
# Celery results.
CELERY_RESULT_BACKEND = os.environ.get(
    "APP_CACHE_REDIS_URL",
    "redis://localhost:6379/1")
# Celery accepted content types.
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']

###############################################################################
# Cache
###############################################################################

CACHE_KEY_PREFIX = "cache::"
CACHE_REDIS_URL = os.environ.get(
    "APP_CACHE_REDIS_URL",
    "redis://localhost:6379/0")
CACHE_TYPE = "redis"

###############################################################################
# Database
###############################################################################

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://localhost/cds")
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = True

###############################################################################
# Debugbar
###############################################################################

DEBUG_TB_ENABLED = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

###############################################################################
# Search
###############################################################################

# Search API endpoint.
SEARCH_UI_SEARCH_API = "/api/records/"
# Default template for search UI.
SEARCH_UI_SEARCH_TEMPLATE = "cds_search_ui/search.html"
# Default Elasticsearch document type.
SEARCH_DOC_TYPE_DEFAULT = None
# Do not map any keywords.
SEARCH_ELASTIC_KEYWORD_MAPPING = {}
# SEARCH UI JS TEMPLATES
# SEARCH_UI_JSTEMPLATE_RESULTS = 'templates/cds_search_ui/results.html'

###############################################################################
# REST API
###############################################################################

# FIXME: Enable CORS for now.
REST_ENABLE_CORS = True

###############################################################################
# Records
###############################################################################

# Endpoints for records.
RECORDS_UI_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        route='/record/<pid_value>',
        template='cds_records/record_detail.html',
    ),
    record_preview=dict(
        pid_type='recid',
        route='/record/<pid_value>/preview/<filename>',
        view_imp='invenio_previewer.views.preview',
    ),
    record_files=dict(
        pid_type='recid',
        route='/record/<pid_value>/files/<filename>',
        view_imp='invenio_files_rest.views.file_download_ui',
    ),
)

# OAI Server.
OAISERVER_ID_PREFIX = 'oai:cds.cern.ch:'
OAISERVER_RECORD_INDEX = 'records'

# 404 template.
RECORDS_UI_TOMBSTONE_TEMPLATE = "invenio_records_ui/tombstone.html"

# Endpoints for record API.
RECORDS_REST_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        pid_minter='recid',
        pid_fetcher='recid',
        search_index='records',
        search_type=None,
        search_factory_imp='invenio_records_rest.query.es_search_factory',
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/records/',
        item_route='/record/<pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
    ),
)

# Sort options records REST API.
RECORDS_REST_SORT_OPTIONS = dict(
    records=dict(
        bestmatch=dict(
            title='Best match',
            fields=['-_score'],
            default_order='asc',
            order=1,
        ),
        controlnumber=dict(
            title='Control number',
            fields=['control_number'],
            default_order='desc',
            order=2,
        )
    )
)

# Default sort for records REST API.
RECORDS_REST_DEFAULT_SORT = dict(
    records=dict(query='bestmatch', noquery='-controlnumber'),
)

# Defined facets for records REST API.
RECORDS_REST_FACETS = dict(
    records=dict(
        aggs=dict(
            authors=dict(terms=dict(
                field='main_entry_personal_name.personal_name.untouched')),
            languages=dict(terms=dict(
                field='language_code.language_code_of_text_'
                      'sound_track_or_separate_title')),
            topic=dict(terms=dict(
                field='subject_added_entry_topical_term.'
                      'topical_term_or_geographic_name_entry_element')),
        ),
        post_filters=dict(
            authors=terms_filter(
                'main_entry_personal_name.personal_name.untouched'),
            languages=terms_filter(
                'language_code.language_code_of_text_'
                'sound_track_or_separate_title'),
            topic=terms_filter(
                'subject_added_entry_topical_term.'
                'topical_term_or_geographic_name_entry_element'),
        )
    )
)

# Add tuple as array type on record validation
# http://python-jsonschema.readthedocs.org/en/latest/validate/#validating-types
RECORDS_VALIDATION_TYPES = dict(
    array=(list, tuple),
)

# FIXME: Disable permissions for now.
RECORDS_UI_DEFAULT_PERMISSION_FACTORY = None

###############################################################################
# Formatter
###############################################################################
#: List of allowed titles in badges.
FORMATTER_BADGES_ALLOWED_TITLES = ['DOI', 'doi']

#: Mapping of titles.
FORMATTER_BADGES_TITLE_MAPPING = {'doi': 'DOI'}

###############################################################################
# Home page
###############################################################################

# Display a homepage.
FRONTPAGE_ENDPOINT = "cds_home.index"

###############################################################################
# Security
###############################################################################

# Disable registrations.
SECURITY_REGISTERABLE = False
# Security login salt.
SECURITY_LOGIN_SALT = 'CHANGE_ME'

###############################################################################
# Theme
###############################################################################

# The site name
THEME_SITENAME = _("CERN Document Server")
# The theme logo.
THEME_LOGO = 'img/cds.svg'
# The base template.
BASE_TEMPLATE = "cds_theme/page.html"
# Header template for entire site.
HEADER_TEMPLATE = "cds_theme/header.html"
# RequireJS configuration.
REQUIREJS_CONFIG = "js/cds-build.js"
# Endpoint for breadcrumb root.
THEME_BREADCRUMB_ROOT_ENDPOINT = 'cds_home.index'

###############################################################################
# Previewer
###############################################################################

# Base CSS bundle to include in all previewers
PREVIEWER_BASE_CSS_BUNDLES = ['cds_theme_css']
# Base JS bundle to include in all previewers
PREVIEWER_BASE_JS_BUNDLES = ['cds_theme_js']

###############################################################################
# Storage
###############################################################################

# FIXME: Add proper data location
DATADIR = '/tmp'

###############################################################################
# Logging
###############################################################################

#: Overwrite default Sentry extension class to support Sentry 6.
LOGGING_SENTRY_CLASS = 'invenio_logging.sentry6:Sentry6'


###############################################################################
# JSON Schemas
###############################################################################

JSONSCHEMAS_HOST = os.environ.get("JSONSCHEMAS_HOST", "localhost:5000")
