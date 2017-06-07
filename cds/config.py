# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS base Invenio configuration."""

from __future__ import absolute_import, print_function

import os
from datetime import timedelta

from invenio_deposit.config import DEPOSIT_REST_FACETS
from invenio_deposit.scopes import write_scope
from invenio_deposit.utils import check_oauth2_scope
from invenio_oauthclient.contrib import cern
from invenio_opendefinition.config import OPENDEFINITION_REST_ENDPOINTS
from invenio_records_rest.facets import range_filter, terms_filter

from .modules.deposit.facets import created_by_me_aggs
from .modules.records.permissions import (deposit_delete_permission_factory,
                                          deposit_read_permission_factory,
                                          deposit_update_permission_factory,
                                          record_create_permission_factory,
                                          record_read_permission_factory,
                                          record_update_permission_factory)
from .modules.records.search import NotDeletedKeywordSearch, RecordVideosSearch


# Identity function for string extraction
def _(x):
    """Identity function."""
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

# Celery broker.
BROKER_URL = os.environ.get(
    'APP_BROKER_URL',
    'redis://localhost:6379/0')
# Celery results.
CELERY_RESULT_BACKEND = os.environ.get(
    'APP_CACHE_REDIS_URL',
    'redis://localhost:6379/1')
# Celery monitoring.
CELERY_TRACK_STARTED = True
# Celery accepted content types.
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml', 'pickle']
# Celery Beat schedule
CELERYBEAT_SCHEDULE = {
    'indexer': {
        'task': 'invenio_indexer.tasks.process_bulk_queue',
        'schedule': timedelta(minutes=5),
    },
    'keywords': {
        'task': 'cds.modules.records.tasks.keywords_harvesting',
        'schedule': timedelta(days=1),
    },
    'sessions': {
        'task': 'invenio_accounts.tasks.clean_session_table',
        'schedule': timedelta(days=1),
    },
    'tasks_status': {
        'task': 'cds.modules.deposit.tasks.preserve_celery_states_on_db',
        'schedule': timedelta(days=1),
    },
}

###############################################################################
# Cache
###############################################################################

CACHE_KEY_PREFIX = 'cache::'
CACHE_REDIS_URL = os.environ.get(
    'APP_CACHE_REDIS_URL',
    'redis://localhost:6379/0')
CACHE_TYPE = 'redis'

###############################################################################
# Database
###############################################################################

SQLALCHEMY_DATABASE_URI = os.environ.get(
    'SQLALCHEMY_DATABASE_URI',
    'postgresql+psycopg2://localhost/cds', )
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = True

###############################################################################
# Debugbar
###############################################################################
DEBUG = True
DEBUG_TB_ENABLED = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

###############################################################################
# Search
###############################################################################

# Search API endpoint.
SEARCH_UI_SEARCH_API = '/api/records/'
# Default template for search UI.
SEARCH_UI_SEARCH_TEMPLATE = 'cds_search_ui/search.html'
# Default base template for search UI
SEARCH_UI_BASE_TEMPLATE = 'cds_theme/page.html'
# Default Elasticsearch document type.
SEARCH_DOC_TYPE_DEFAULT = None
# Do not map any keywords.
SEARCH_ELASTIC_KEYWORD_MAPPING = {}
# SEARCH UI JS TEMPLATES
# SEARCH_UI_JSTEMPLATE_RESULTS = 'templates/cds_search_ui/results.html'

# Angular template for featured
SEARCH_UI_VIDEO_FEATURED = 'templates/cds/video/featured.html'
# Angular template for medium size (used for recent)
SEARCH_UI_VIDEO_MEDIUM = 'templates/cds/video/featured-medium.html'
# Angular template for small size (used for search results)
SEARCH_UI_VIDEO_SMALL = 'templates/cds/video/small.html'

###############################################################################
# REST API
###############################################################################

# FIXME: Enable CORS for now.
REST_ENABLE_CORS = True

###############################################################################
# Records
###############################################################################

# Mapping of export formats to content type.
CDS_RECORDS_EXPORTFORMATS = {
    'json': dict(
        title='JSON',
        mimetype='application/json',
        serializer='invenio_records_rest.serializers:json_v1'
    ),
    'smil': dict(
        title='SMIL',
        mimetype='application/smil',
        serializer='cds.modules.records.serializers:smil_v1'
    ),
    'vtt': dict(
        title='VTT',
        mimetype='text/vtt',
        serializer='cds.modules.records.serializers:vtt_v1'
    ),
    'drupal': dict(
        title='Drupal',
        mimetype='x-application/drupal',
        serializer='cds.modules.records.serializers:drupal_v1'
    ),
    'dcite': dict(
        title='Datacite XML v3.1',
        mimetype='application/x-datacite+xml',
        serializer='cds.modules.records.serializers:datacite_v31'
    )
}

CDS_RECORDS_UI_LINKS_FORMAT = "https://cds.cern.ch/record/{recid}"

# Endpoints for records.
RECORDS_UI_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        route='/record/<pid_value>',
        template='cds_records/record_detail.html',
        record_class='cds.modules.records.api:CDSRecord',
    ),
    recid_preview=dict(
        pid_type='recid',
        route='/record/<pid_value>/preview/<filename>',
        view_imp='cds.modules.previewer.views.preview_recid',
        record_class='cds.modules.records.api:CDSRecord',
    ),
    recid_embed=dict(
        pid_type='recid',
        route='/record/<pid_value>/embed/<filename>',
        view_imp='cds.modules.previewer.views.preview_recid_embed',
        record_class='cds.modules.records.api:CDSRecord',
    ),
    recid_embed_default=dict(
        pid_type='recid',
        route='/record/<pid_value>/embed',
        view_imp='cds.modules.previewer.views.preview_recid_embed',
        record_class='cds.modules.records.api:CDSRecord',
    ),
    recid_files=dict(
        pid_type='recid',
        route='/record/<pid_value>/files/<filename>',
        view_imp='invenio_records_files.utils:file_download_ui',
        record_class='cds.modules.records.api:CDSRecord',
    ),
    video_preview=dict(
        pid_type='depid',
        route='/deposit/<pid_value>/preview/video/<filename>',
        view_imp='cds.modules.previewer.views.preview_depid',
        record_class='cds.modules.deposit.api:Video',
    ),
    project_preview=dict(
        pid_type='depid',
        route='/deposit/<pid_value>/preview/project/<filename>',
        view_imp='cds.modules.previewer.views.preview_depid',
        record_class='cds.modules.deposit.api:Project',
    ),
    recid_export=dict(
        pid_type='recid',
        route='/record/<pid_value>/export/<any({0}):format>'.format(
            ", ".join(list(CDS_RECORDS_EXPORTFORMATS.keys()))
        ),
        template='cds_records/record_export.html',
        view_imp='cds.modules.records.views.records_ui_export',
        record_class='cds.modules.records.api:CDSRecord',
    ),
)

# OAI Server.
OAISERVER_ID_PREFIX = 'oai:cds.cern.ch:'
OAISERVER_RECORD_INDEX = 'records'

# 404 template.
RECORDS_UI_TOMBSTONE_TEMPLATE = 'invenio_records_ui/tombstone.html'

# Endpoints for record API.
_Record_PID = 'pid(recid, record_class="cds.modules.records.api:CDSRecord")'
_Category_PID = 'pid(catid, record_class="cds.modules.records.api:Category")'
_Keyword_PID = 'pid(kwid, record_class="cds.modules.records.api:Keyword")'
RECORDS_REST_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        pid_minter='cds_recid',
        pid_fetcher='cds_recid',
        search_type=None,
        search_class=RecordVideosSearch,
        search_factory_imp='invenio_records_rest.query.es_search_factory',
        record_serializers={
            'application/json': ('cds.modules.records.serializers'
                                 ':json_v1_response'),
            'application/smil': ('cds.modules.records.serializers'
                                 ':smil_v1_response'),
            'text/vtt': ('cds.modules.records.serializers'
                         ':vtt_v1_response'),
            'x-application/drupal': ('cds.modules.records.serializers'
                                     ':drupal_v1_response'),
            'application/x-datacite+xml': (
                'cds.modules.records.serializers.datacite_v31_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/records/',
        item_route='/record/<{0}:pid_value>'.format(_Record_PID),
        default_media_type='application/json',
        max_result_window=10000,
        read_permission_factory_imp=record_read_permission_factory,
        links_factory_imp='cds.modules.records.links.record_link_factory',
    ),
    catid=dict(
        default_endpoint_prefix=True,
        pid_type='catid',
        pid_minter='cds_catid',
        pid_fetcher='cds_catid',
        search_index='categories',
        search_type=None,
        search_class=RecordVideosSearch,
        search_factory_imp='invenio_records_rest.query.es_search_factory',
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/categories/',
        item_route='/categories/<{0}:pid_value>'.format(_Category_PID),
        default_media_type='application/json',
        max_result_window=10000,
        suggesters={
            'suggest-name': {
                'completion': {
                    'field': 'suggest_name',
                }
            }
        },
        read_permission_factory_imp=record_read_permission_factory,
    ),
    kwid=dict(
        default_endpoint_prefix=True,
        pid_type='kwid',
        pid_minter='cds_kwid',
        pid_fetcher='cds_kwid',
        search_index='keywords',
        search_type=None,
        search_class=NotDeletedKeywordSearch,
        search_factory_imp='invenio_records_rest.query.es_search_factory',
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/keywords/',
        item_route='/keywords/<{0}:pid_value>'.format(_Keyword_PID),
        default_media_type='application/json',
        max_result_window=10000,
        suggesters={
            'suggest-name': {
                'completion': {
                    'field': 'suggest_name',
                }
            }
        },
        read_permission_factory_imp=record_read_permission_factory,
    ),
)

RECORDS_REST_ENDPOINTS.update(OPENDEFINITION_REST_ENDPOINTS)

# Sort options records REST API.
RECORDS_REST_SORT_OPTIONS = dict(
    records=dict(
        bestmatch=dict(
            title='Best match',
            fields=['-_score'],
            default_order='asc',
            order=1,
        ),
    )
)

# Default sort for records REST API.
RECORDS_REST_DEFAULT_SORT = {
    'records': dict(query='bestmatch'),
    'deposits-records-videos-project': dict(
        query='bestmatch',
        noquery='mostrecent',
    )
}

# Defined facets for records REST API.
RECORDS_REST_FACETS = dict()

RECORD_UI_ENDPOINT = '{scheme}://{host}/record/{pid_value}'

# Facets for the specific index
DEPOSIT_PROJECT_FACETS = {
    'deposits-records-videos-project': {
        'aggs': {
            'status': {
                'terms': {'field': '_deposit.status'},
            },
            'category': {
                'terms': {'field': 'category.untouched'},
            },
            'transcode': {
                'terms': {'field': '_deposit.state.file_transcode'},
            },
            'frames': {
                'terms': {'field': '_deposit.state.file_video_extract_frames'},
            },
            'created_by': created_by_me_aggs,
        },
        'post_filters': {
            'status': terms_filter('_deposit.status'),
            'category': terms_filter('category.untouched'),
            'transcode': terms_filter('_deposit.state.file_transcode'),
            'frames': terms_filter('_deposit.state.file_video_extract_frames'),
            'created_by': terms_filter('_deposit.created_by'),
        },
    },
}

RECORD_VIDEOS_FACETS = {
    'records-videos-video': {
        'aggs': {
            'category': {
                'terms': {'field': 'category.untouched'},
            },
            'type': {
                'terms': {'field': 'type.untouched'},
            },
            'license': {
                'terms': {'field': 'license.license.untouched'},
            },
            'years': {
                'date_histogram': {
                    'field': 'date',
                    'interval': 'year',
                    'format': 'yyyy'
                }
            }
        },
        'post_filters': {
            'category': terms_filter('category.untouched'),
            'type': terms_filter('type.untouched'),
            'license': terms_filter('license.license.untouched'),
            'years': range_filter('date', format='yyyy', end_date_math='/y'),
        },
    }
}

# Deposit search index.
DEPOSIT_UI_SEARCH_INDEX = 'deposits-records-videos-project'

# Options for sorting deposits.
DEPOSIT_REST_SORT_OPTIONS = {
    'deposits-records-videos-project': dict(
        bestmatch=dict(
            fields=['-_score'],
            title='Best match',
            default_order='asc',
            order=1
        ),
        mostrecent=dict(
            fields=['-_updated'],
            title='Newest',
            default_order='asc', order=2,

        ),
        oldest=dict(
            fields=['_updated'],
            title='Oldest',
            default_order='asc', order=3,
        ),
        title_asc=dict(
            fields=['title.title.raw'],
            title='Title [Asc]',
            default_order='asc', order=4,
        ),
        title_desc=dict(
            fields=['title.title.raw'],
            title='Title [Desc]',
            default_order='desc', order=5,
        )),
}

# Update facets and sort options with deposit options
RECORDS_REST_SORT_OPTIONS.update(DEPOSIT_REST_SORT_OPTIONS)
RECORDS_REST_FACETS.update(DEPOSIT_REST_FACETS)
RECORDS_REST_FACETS.update(DEPOSIT_PROJECT_FACETS)
RECORDS_REST_FACETS.update(RECORD_VIDEOS_FACETS)
# Add tuple as array type on record validation
# http://python-jsonschema.readthedocs.org/en/latest/validate/#validating-types
RECORDS_VALIDATION_TYPES = dict(
    array=(list, tuple),
)

RECORDS_UI_DEFAULT_PERMISSION_FACTORY = \
    'cds.modules.records.permissions:deposit_read_permission_factory'

# Endpoint for the cds_recid provider
RECORDS_ID_PROVIDER_ENDPOINT = None

###############################################################################
# Files
###############################################################################
FILES_REST_PERMISSION_FACTORY = \
    'cds.modules.records.permissions:files_permission_factory'

# Files storage
FIXTURES_FILES_LOCATION = os.environ.get('APP_FIXTURES_FILES_LOCATION', '/tmp')


###############################################################################
# Formatter
###############################################################################
#: List of allowed titles in badges.
FORMATTER_BADGES_ALLOWED_TITLES = ['DOI', 'doi', 'RN', 'rn']

#: Mapping of titles.
FORMATTER_BADGES_TITLE_MAPPING = {'doi': 'DOI', 'rn': 'RN'}

# Enable badges
FORMATTER_BADGES_ENABLE = True

###############################################################################
# Home page
###############################################################################

# Display a homepage.
FRONTPAGE_ENDPOINT = 'cds_home.index'
# Featured query
FRONTPAGE_FEATURED_QUERY = '/api/records/?featured=1&size=1&sort=mostrecent'
# Recent videos query
FRONTPAGE_RECENT_QUERY = '/api/records/?size=3&sort=mostrecent'
# Queries for the boxes
FRONTPAGE_QUERIES = [
    {'size': 5, 'page': 1},
    {'size': 5, 'page': 1},
    {'size': 5, 'page': 1},
]
# Quote before search box
FRONTPAGE_SLOGAN = 'Search for over than 1.000.000 records'

###############################################################################
# Security
###############################################################################

# Disable advanced features.
SECURITY_REGISTERABLE = False
SECURITY_RECOVERABLE = False
SECURITY_CONFIRMABLE = False
SECURITY_CHANGEABLE = False
PERMANENT_SESSION_LIFETIME = timedelta(1)

# Override login template.
SECURITY_LOGIN_USER_TEMPLATE = 'cds_theme/login_user.html'

# Security login salt.
SECURITY_LOGIN_SALT = 'CHANGE_ME'

###############################################################################
# User Profiles
###############################################################################

# Override profile template.
USERPROFILES_PROFILE_TEMPLATE = 'cds_theme/profile.html'
USERPROFILES_EMAIL_ENABLED = False

###############################################################################
# OAuth
###############################################################################

OAUTHCLIENT_REMOTE_APPS = dict(
    cern=cern.REMOTE_APP,
)
#: Credentials for CERN OAuth (must be changed to work).
CERN_APP_CREDENTIALS = dict(
    consumer_key='CHANGE_ME',
    consumer_secret='CHANGE_ME',
)

###############################################################################
# Theme
###############################################################################

# The site name
THEME_SITENAME = _('CERN Document Server')
# The theme logo.
THEME_LOGO = False
# The base template.
BASE_TEMPLATE = 'cds_theme/page.html'
# Header template for entire site.
HEADER_TEMPLATE = 'cds_theme/header.html'
# RequireJS configuration.
REQUIREJS_CONFIG = 'js/cds-build.js'
# Endpoint for breadcrumb root.
THEME_BREADCRUMB_ROOT_ENDPOINT = 'cds_home.index'
# Cover template
COVER_TEMPLATE = 'cds_theme/page_cover.html'
# 404 Error
THEME_404_TEMPLATE = 'cds_theme/error/404.html'
# 500 Error
THEME_500_TEMPLATE = 'cds_theme/error/500.html'
# Error template
THEME_ERROR_TEMPLATE = 'cds_theme/error/base.html'

###############################################################################
# Previewer
###############################################################################

# Base CSS bundle to include in all previewers
PREVIEWER_BASE_CSS_BUNDLES = ['cds_theme_css']
# Base JS bundle to include in all previewers
PREVIEWER_BASE_JS_BUNDLES = ['cds_theme_js']
# Decides which previewers are available and their priority.
PREVIEWER_PREFERENCE = [
    'csv_dthreejs',
    'simple_image',
    'json_prismjs',
    'xml_prismjs',
    'mistune',
    'pdfjs',
    'ipynb',
    'cds_video',
    'cds_embed_video',
    'zip',
    'cds_deposit_video',
]
# Licence key for THEO player
THEO_LICENCE_KEY = 'CHANGE_ME'
# Wowza server URL for m3u8 playlist generation
WOWZA_PLAYLIST_URL = ('https://wowzaqaedge.cern.ch/cdseos/_definist_/smil:'
                      '{filepath}/playlist.m3u8')
WOWZA_VIDEO_URL = \
    'https://wowzaqaedge.cern.ch/cdseos/_definist_/mp4:%s/playlist.m3u8'
# Size
VIDEO_POSTER_SIZE = (180, 101)

###############################################################################
# Logging
###############################################################################

#: Overwrite default Sentry extension class to support Sentry 6.
LOGGING_SENTRY_CLASS = 'invenio_logging.sentry6:Sentry6'

###############################################################################
# JSON Schemas
###############################################################################

JSONSCHEMAS_ENDPOINT = '/schemas'
JSONSCHEMAS_HOST = os.environ.get('JSONSCHEMAS_HOST', 'localhost:5000')
JSONSCHEMAS_URL_SCHEME = 'https'

###############################################################################
# Migration
###############################################################################

MIGRATOR_RECORDS_DUMPLOADER_CLS = 'cds.modules.migrator.records:' \
                                  'CDSRecordDumpLoader'
MIGRATOR_RECORDS_DUMP_CLS = 'cds.modules.migrator.records:CDSRecordDump'

###############################################################################
# Indexer
###############################################################################

INDEXER_DEFAULT_INDEX = 'records-default-v1.0.0'
INDEXER_DEFAULT_DOC_TYPE = 'default-v1.0.0'
INDEXER_BULK_REQUEST_TIMEOUT = 60


###############################################################################
# Deposit
###############################################################################
#: DOI prefixes considered as local prefixes.
CDS_LOCAL_DOI_PREFIXES = ['10.5072', '10.17181']

#: DataCite API - Prefix for minting DOIs in (10.5072 is a test prefix).
PIDSTORE_DATACITE_DOI_PREFIX = '10.5072'
# PID minter used for record submissions.
DEPOSIT_PID_MINTER = 'cds_recid'
#: Enable the DataCite minding of DOIs after Deposit publishing
DEPOSIT_DATACITE_MINTING_ENABLED = False

# Template for deposit list view.
DEPOSIT_UI_INDEX_TEMPLATE = 'cds_deposit/index.html'
# Template to use for UI.
DEPOSIT_UI_NEW_TEMPLATE = 'cds_deposit/edit.html'
# The schema form deposit
DEPOSIT_DEFAULT_SCHEMAFORM = 'json/cds_deposit/forms/project.json'
# Default schema for the deposit
DEPOSIT_DEFAULT_JSONSCHEMA = \
    'deposits/records/videos/project/project-v1.0.0.json'
# Deposit schemas
DEPOSIT_JSONSCHEMA = {
    'project': 'deposits/records/videos/project/project-v1.0.0.json',
    'video': 'deposits/records/videos/video/video-v1.0.0.json',
}
# Template for <invenio-records-form> directive
DEPOSIT_UI_JSTEMPLATE_FORM = 'templates/cds_deposit/form.html'
DEPOSIT_UI_JSTEMPLATE_ACTIONS = 'templates/cds_deposit/actions.html'
DEPOSIT_SEARCH_API = '/api/deposits/project/'
_CDSDeposit_PID = \
    'pid(depid,record_class="cds.modules.deposit.api:CDSDeposit")'
_Project_PID = 'pid(depid,record_class="cds.modules.deposit.api:Project")'
_Video_PID = 'pid(depid,record_class="cds.modules.deposit.api:Video")'
DEPOSIT_UI_ENDPOINT_DEFAULT = '{scheme}://{host}/deposit/{pid_value}'
DEPOSIT_UI_ENDPOINT = '{scheme}://{host}/deposit/{type}/{pid_value}'
DEPOSIT_RECORDS_API_DEFAULT = '/api/deposits/{pid_value}'
DEPOSIT_RECORDS_API = '/api/deposits/{type}/{pid_value}'
# use a custom function to catch record publish signals
DEPOSIT_REGISTER_SIGNALS = False
# Deposit rest endpoints
DEPOSIT_REST_ENDPOINTS = dict(
    depid=dict(
        pid_type='depid',
        pid_minter='deposit',
        pid_fetcher='deposit',
        default_endpoint_prefix=True,
        record_class='cds.modules.deposit.api:CDSDeposit',
        files_serializers={
            'application/json': ('invenio_deposit.serializers'
                                 ':json_v1_files_response'),
        },
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_class='invenio_deposit.search:DepositSearch',
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/deposits/',
        item_route='/deposits/<{0}:pid_value>'.format(_CDSDeposit_PID),
        file_list_route='/deposits/<{0}:pid_value>/files'.format(
            _CDSDeposit_PID),
        file_item_route='/deposits/<{0}:pid_value>/files/<path:key>'.format(
            _CDSDeposit_PID),
        default_media_type='application/json',
        links_factory_imp='cds.modules.deposit.links:deposit_links_factory',
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(
                record=record).can(),
            write_scope.id),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: record_update_permission_factory(
                record=record).can(),
            write_scope.id),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(
                record=record).can(),
            write_scope.id),
        max_result_window=10000,
    ),
    project=dict(
        pid_type='depid',
        pid_minter='deposit',
        pid_fetcher='deposit',
        default_endpoint_prefix=False,
        record_class='cds.modules.deposit.api:Project',
        search_factory_imp='cds.modules.deposit.search:deposit_search_factory',
        record_loaders={
            'application/json': 'cds.modules.deposit.loaders:project_loader',
            'application/vnd.project.partial+json':
                'cds.modules.deposit.loaders:partial_project_loader',
        },
        files_serializers={
            'application/json': ('invenio_deposit.serializers'
                                 ':json_v1_files_response'),
        },
        record_serializers={
            'application/json': ('cds.modules.records.serializers'
                                 ':cdsdeposit_json_v1_response'),
            'application/vnd.project.partial+json': (
                'cds.modules.records.serializers'
                ':cdsdeposit_json_v1_response'),
        },
        search_class='cds.modules.deposit.search:DepositVideosSearch',
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/deposits/project/',
        item_route='/deposits/project/<{0}:pid_value>'.format(_Project_PID),
        file_list_route='/deposits/project/<{0}:pid_value>/files'.format(
            _Project_PID),
        file_item_route='/deposits/project/<{0}:pid_value>/files/<path:key>'
        .format(_Project_PID),
        default_media_type='application/json',
        links_factory_imp='cds.modules.deposit.links:project_links_factory',
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(
                record=record).can(),
            write_scope.id),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_update_permission_factory(
                record=record).can(),
            write_scope.id),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(
                record=record).can(),
            write_scope.id),
        max_result_window=10000,
    ),
    video=dict(
        pid_type='depid',
        pid_minter='deposit',
        pid_fetcher='deposit',
        default_endpoint_prefix=False,
        record_class='cds.modules.deposit.api:Video',
        record_loaders={
            'application/json': 'cds.modules.deposit.loaders:video_loader',
            'application/vnd.video.partial+json':
                'cds.modules.deposit.loaders:partial_video_loader'
        },
        files_serializers={
            'application/json': ('invenio_deposit.serializers'
                                 ':json_v1_files_response'),
        },
        record_serializers={
            'application/json': ('cds.modules.records.serializers'
                                 ':cdsdeposit_json_v1_response'),
            'application/vnd.video.partial+json': (
                'cds.modules.records.serializers'
                ':cdsdeposit_json_v1_response'),
        },
        search_class='invenio_deposit.search:DepositSearch',
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/deposits/video/',
        item_route='/deposits/video/<{0}:pid_value>'.format(_Video_PID),
        file_list_route='/deposits/video/<{0}:pid_value>/files'.format(
            _Video_PID),
        file_item_route='/deposits/video/<{0}:pid_value>/files/<path:key>'
        .format(_Video_PID),
        default_media_type='application/json',
        links_factory_imp='cds.modules.deposit.links:video_links_factory',
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(
                record=record).can(),
            write_scope.id),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_update_permission_factory(
                record=record).can(),
            write_scope.id),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(
                record=record).can(),
            write_scope.id),
        max_result_window=10000,
    ),
)

# Deposit UI endpoints
DEPOSIT_RECORDS_UI_ENDPOINTS = {
    'video_new': {
        'pid_type': 'depid',
        'route': '/deposit/video/new',
        'template': 'cds_deposit/edit.html',
        'record_class': 'cds.modules.deposit.api:CDSDeposit',
    },
    'depid': {
        'pid_type': 'depid',
        'route': '/deposit/<pid_value>',
        'template': 'cds_deposit/edit.html',
        'record_class': 'cds.modules.deposit.api:CDSDeposit',
    },
    'project': {
        'pid_type': 'depid',
        'route': '/deposit/project/<pid_value>',
        'template': 'cds_deposit/edit.html',
        'record_class': 'cds.modules.deposit.api:Project',
        'view_imp': 'cds.modules.deposit.views:project_view'
    },
}
# Deposit successful messages
DEPOSIT_RESPONSE_MESSAGES = dict(
    self=dict(
        message="Saved successfully."
    ),
    delete=dict(
        message="Deleted succesfully."
    ),
    discard=dict(
        message="Changes discarded succesfully."
    ),
    publish=dict(
        message="Published succesfully."
    ),
    edit=dict(
        message="Edited succesfully."
    ),
)

DEPOSIT_FORM_TEMPLATES_BASE = 'templates/cds_deposit/angular-schema-form'
DEPOSIT_FORM_TEMPLATES = {
    'default': 'default.html',
    'fieldset': 'fieldset.html',
    'ckeditor': 'ckeditor.html',
    'uiselect': 'uiselect.html',
    'array': 'array.html',
    'radios_inline': 'radios_inline.html',
    'radios': 'radios.html',
    'select': 'select.html',
    'button': 'button.html',
    'textarea': 'textarea.html',
    'checkbox': 'checkbox.html',
    'uiselectmultiple': 'uiselectmultiple.html',
    'strapselect': 'strapselect.html',
}

# App key for uploading files from dropbox
DEPOSIT_DROPBOX_APP_KEY = 'CHANGE_ME'

# Default copyright holder & url
DEPOSIT_AVC_COPYRIGHT = {
    'holder': 'CERN',
    'url': 'http://copyright.web.cern.ch',
}

###############################################################################
# SSE
###############################################################################
SSE_REDIS_URL = 'redis://localhost:6379/1'

###############################################################################
# Keywords
###############################################################################
CDS_KEYWORDS_HARVESTER_URL = 'http://home.cern/api/tags-json-feed'

# OpenDefinition
# ==============
#: Hostname for OpenAIRE's grant resolver.
OPENDEFINITION_JSONRESOLVER_HOST = 'cds.cern.ch'
