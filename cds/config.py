# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016, 2017, 2018, 2019 CERN.
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

import ast
import os
from datetime import timedelta

from celery.schedules import crontab
from opensearchpy import RequestsHttpConnection
from flask import current_app, session
from flask_login import current_user
from invenio_app.config import APP_DEFAULT_SECURE_HEADERS
from invenio_opendefinition.config import OPENDEFINITION_REST_ENDPOINTS
from invenio_records_rest.facets import range_filter, terms_filter
from invenio_stats.aggregations import StatAggregator
from invenio_stats.tasks import StatsAggregationTask, StatsEventTask
from invenio_stats.processors import EventsIndexer, anonymize_user, flag_robots
from invenio_stats.queries import DateHistogramQuery, TermsQuery

from .modules.invenio_deposit.config import DEPOSIT_REST_FACETS
from .modules.invenio_deposit.scopes import write_scope
from .modules.invenio_deposit.utils import check_oauth2_scope
from .modules.deposit.facets import created_by_me_aggs
from .modules.deposit.indexer import CDSRecordIndexer
from .modules.records.permissions import (
    deposit_delete_permission_factory,
    deposit_read_permission_factory,
    deposit_update_permission_factory,
    record_create_permission_factory,
    record_read_permission_factory,
    record_update_permission_factory,
)
from .modules.records.search import (
    NotDeletedKeywordSearch,
    RecordVideosSearch,
    lowercase_filter,
)
from .modules.stats.event_builders import (
    build_file_unique_id,
    build_record_unique_id,
    drop_undesired_fields,
    filter_by_reportnumber,
)


# Identity function for string extraction
def _(x):
    """Identity function."""
    return x


def _parse_env_bool(var_name, default=None):
    if str(os.environ.get(var_name)).lower() == "true":
        return True
    elif str(os.environ.get(var_name)).lower() == "false":
        return False
    return default


#: Email address for admins.
CDS_ADMIN_EMAIL = "cds-admin@cern.ch"
#: Email address for no-reply.
NOREPLY_EMAIL = "no-reply@cern.ch"
MAIL_SUPPRESS_SEND = True

# Rate limiting
# =============
RATELIMIT_ENABLED = False

###############################################################################
# Translations & Time
###############################################################################

# Default language.
BABEL_DEFAULT_LANGUAGE = "en"
# Default timezone.
BABEL_DEFAULT_TIMEZONE = "Europe/Zurich"

###############################################################################
# Celery
###############################################################################

#: URL of message broker for Celery (default is RabbitMQ).
CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672/"
#: URL of backend for result storage (default is Redis).
CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
# Celery monitoring.
CELERY_TASK_TRACK_STARTED = True
# Celery accepted content types.
CELERY_ACCEPT_CONTENT = ["json", "msgpack", "yaml"]
"""A whitelist of content-types/serializers."""

# Celery Beat schedule
CELERY_BEAT_SCHEDULE = {
    "indexer": {
        "task": "invenio_indexer.tasks.process_bulk_queue",
        "schedule": timedelta(minutes=5),
    },
    "keywords": {
        "task": "cds.modules.records.tasks.keywords_harvesting",
        "schedule": crontab(minute=10, hour=0),
    },
    "sessions": {
        "task": "invenio_accounts.tasks.clean_session_table",
        "schedule": crontab(minute=0, hour=0),
    },
    "opencast_check_transcoding_status": {
        "task": "cds.modules.opencast.tasks.check_transcoding_status",
        "schedule": timedelta(seconds=10),
    },
    "file-checks": {
        "task": "invenio_files_rest.tasks.schedule_checksum_verification",
        "schedule": timedelta(hours=1),
        "kwargs": {
            "batch_interval": {"hours": 1},
            "frequency": {"days": 14},
            "max_count": 0,
        },
    },
    "hard-file-checks": {
        "task": "invenio_files_rest.tasks.schedule_checksum_verification",
        "schedule": timedelta(hours=1),
        "kwargs": {
            "batch_interval": {"hours": 1},
            # Manually check and calculate checksums of files biannually
            "frequency": {"days": 180},
            # Split batches based on total files size
            "max_size": 0,
            # Actual checksum calculation, instead of relying on a EOS query
            "checksum_kwargs": {"use_default_impl": True},
        },
    },
    "index-deposit-projects": {
        "task": "cds.modules.deposit.tasks.index_deposit_projects",
        # Every 12 minutes, not to be at the same time as the others
        "schedule": timedelta(minutes=12),
    },
    "clean-tmp-videos": {
        "task": "cds.modules.maintenance.tasks.clean_tmp_videos",
        "schedule": crontab(minute=0, hour=3),  # at 3 am
    },
    # indexing of statistics events & aggregations
    "stats-process-events": {
        **StatsEventTask,
        "schedule": timedelta(seconds=10),  # Every hour at minute 25 and 55
        "args": [("record-view", "file-download", "media-record-view")],
    },
    "stats-aggregate-events": {
        **StatsAggregationTask,
        "schedule": timedelta(seconds=10),  # Every hour at minute 0
        "args": [
            (
                "record-view-agg",
                "media-record-view-agg",
                "file-download-agg",
            )
        ],
    },
    # 'file-integrity-report': {
    #     'task': 'cds.modules.records.tasks.file_integrity_report',
    #     'schedule': crontab(minute=0, hour=7),  # Every day at 07:00 UTC
    # },
    # 'subformats-integrity-report': {
    #     'task': 'cds.modules.records.tasks.subformats_integrity_report',
    #     # Every 2 days at 04:00 UTC
    #     'schedule': crontab(minute=0, hour=4, day_of_week=[0, 2, 4, 6]),
    # },
    # 'missing-subformats-report': {
    #     'task': 'cds.modules.records.tasks.missing_subformats_report',
    #     # Every Monday morning at 05:30 UTC
    #     'schedule': crontab(hour=5, minute=30, day_of_week=1),
    # },
}

###############################################################################
# Cache
###############################################################################

CACHE_KEY_PREFIX = "cache::"
CACHE_REDIS_URL = "redis://localhost:6379/0"
CACHE_TYPE = "redis"
# We use `invenio_cache.cached_unless_authenticated` decorator
# for cahcing the home page. As a result we use the below config
# variable from invenio_cache module to define our caching conditions.
# See <https://github.com/inveniosoftware/invenio-cache/blob/master/invenio_cache/decorators.py#L41>
CACHE_IS_AUTHENTICATED_CALLBACK = (
    lambda: "_flashes" in session or current_user.is_authenticated or current_app.debug
)

###############################################################################
# IIIF
###############################################################################

IIIF_CACHE_REDIS_URL = "redis://localhost:16379/0"
IIIF_CACHE_TIME = "36000"  # 10 hours
IIIF_CACHE_HANDLER = "flask_iiif.cache.redis:ImageRedisCache"

###############################################################################
# Database
###############################################################################

SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://cds-videos:cds-videos@localhost/cds-videos"
)
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = True

###############################################################################
# Debug
###############################################################################
DEBUG = True
DEBUG_TB_ENABLED = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

###############################################################################
# Sentry
###############################################################################
SENTRY_SDK = True
"""Use of sentry-python SDK, if false raven will be used."""
LOGGING_SENTRY_LEVEL = "WARNING"
"""Sentry logging level."""
LOGGING_SENTRY_PYWARNINGS = False
"""Enable logging of Python warnings to Sentry."""
LOGGING_SENTRY_CELERY = False
"""Configure Celery to send logging to Sentry."""
SENTRY_DSN = None
"""Set SENTRY_DSN environment variable."""
# Sentry uses env var SENTRY_ENVIRONMENT and SENTRY_RELEASE

###############################################################################
# Search
###############################################################################
ELASTICSEARCH_HOSTS = ast.literal_eval(
    os.environ.get("ELASTICSEARCH_HOSTS", "['localhost']")
)
ELASTICSEARCH_PORT = int(os.environ.get("ELASTICSEARCH_PORT", "9200"))
ELASTICSEARCH_USER = os.environ.get("ELASTICSEARCH_USER")
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD")
ELASTICSEARCH_URL_PREFIX = os.environ.get("ELASTICSEARCH_URL_PREFIX", "")
ELASTICSEARCH_USE_SSL = _parse_env_bool("ELASTICSEARCH_USE_SSL")
ELASTICSEARCH_VERIFY_CERTS = _parse_env_bool("ELASTICSEARCH_VERIFY_CERTS")

es_hosts = []
for host in ELASTICSEARCH_HOSTS:
    es_host = {"host": host, "port": ELASTICSEARCH_PORT}
    if ELASTICSEARCH_USER and ELASTICSEARCH_PASSWORD:
        es_host["http_auth"] = (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD)
    if ELASTICSEARCH_URL_PREFIX:
        es_host["url_prefix"] = ELASTICSEARCH_URL_PREFIX
    if ELASTICSEARCH_USE_SSL is not None:
        es_host["use_ssl"] = ELASTICSEARCH_USE_SSL
    if ELASTICSEARCH_VERIFY_CERTS is not None:
        es_host["verify_certs"] = ELASTICSEARCH_VERIFY_CERTS
    es_hosts.append(es_host)

SEARCH_HOSTS = es_hosts
# needed when verify cert is disabled see:
# https://github.com/elastic/elasticsearch-py/issues/712
SEARCH_CLIENT_CONFIG = {"connection_class": RequestsHttpConnection}

# Search API endpoint.
SEARCH_UI_SEARCH_API = "/api/records/"
# Name of the search index used.
SEARCH_UI_SEARCH_INDEX = "records-videos-video"
# Default template for search UI.
SEARCH_UI_SEARCH_TEMPLATE = "cds_search_ui/search.html"
# Default base template for search UI
SEARCH_UI_BASE_TEMPLATE = "cds_theme/page.html"
# Default search parameters for search UI
SEARCH_UI_SEARCH_EXTRA_PARAMS = {"size": 21}  # page size
# Default Elasticsearch document type.
SEARCH_DOC_TYPE_DEFAULT = None

# Do not map any keywords.
SEARCH_ELASTIC_KEYWORD_MAPPING = {}
# SEARCH UI JS TEMPLATES
# SEARCH_UI_JSTEMPLATE_RESULTS = 'templates/cds_search_ui/results.html'
SEARCH_UI_JSTEMPLATE_ERROR = "templates/cds_search_ui/error.html"

# Angular template for featured
SEARCH_UI_VIDEO_FEATURED = "templates/cds/video/featured.html"
# Angular template for medium size (used for recent)
SEARCH_UI_VIDEO_MEDIUM = "templates/cds/video/featured-medium.html"
# Angular template for small size (used for search results)
SEARCH_UI_VIDEO_SMALL = "templates/cds/video/small.html"

# Invenio-Stats
# =============
# See https://invenio-stats.readthedocs.io/en/latest/configuration.html

STATS_EVENTS = {
    "file-download": {
        "templates": "cds.modules.stats.templates.events.file_download",
        "signal": "cds.modules.stats.views.cds_record_media_downloaded",
        "event_builders": [
            "cds.modules.stats.event_builders.file_download_event_builder"
        ],
        "cls": EventsIndexer,
        "params": {
            "preprocessors": [
                anonymize_user,
                drop_undesired_fields,
                build_file_unique_id,
            ]
        },
    },
    "media-record-view": {
        "templates": "cds.modules.stats.templates.events.media_record_view",
        "signal": "cds.modules.stats.views.cds_record_media_viewed",
        "event_builders": [
            "cds.modules.stats.event_builders.media_record_view_event_builder"
        ],
        "cls": EventsIndexer,
        "params": {
            "preprocessors": [
                anonymize_user,
                drop_undesired_fields,
                build_file_unique_id,
            ]
        },
    },
    "record-view": {
        "templates": "cds.modules.stats.templates.events.record_view",
        "signal": "cds.modules.stats.views.cds_record_viewed",
        "event_builders": [
            "cds.modules.stats.event_builders.record_view_event_builder"
        ],
        "cls": EventsIndexer,
        "params": {
            "preprocessors": [
                flag_robots,
                anonymize_user,
                drop_undesired_fields,
                build_record_unique_id,
            ]
        },
    },
}

STATS_AGGREGATIONS = {
    "file-download-agg": {
        "templates": "cds.modules.stats.templates.aggregations.aggr_file_download",
        "cls": StatAggregator,
        "params": {
            "event": "file-download",
            "field": "unique_id",
            "interval": "day",
            "index_interval": "month",
            "copy_fields": {"file": "file"},
            "query_modifiers": [],
            "metric_fields": {
                "unique_count": (
                    "cardinality",
                    "unique_session_id",
                    {"precision_threshold": 1000},
                ),
            },
        },
    },
    "media-record-view-agg": {
        "templates": "cds.modules.stats.templates.aggregations.aggr_media_record_view",
        "cls": StatAggregator,
        "params": {
            "event": "media-record-view",
            "field": "unique_id",
            "interval": "day",
            "index_interval": "month",
            "copy_fields": {"file": "file", "recid": "recid"},
            "query_modifiers": [],
            "metric_fields": {
                "unique_count": (
                    "cardinality",
                    "unique_session_id",
                    {"precision_threshold": 1000},
                ),
            },
        },
    },
    "record-view-agg": {
        "templates": "cds.modules.stats.templates.aggregations.aggr_record_view",
        "cls": StatAggregator,
        "params": {
            "event": "record-view",
            "field": "unique_id",
            "interval": "day",
            "index_interval": "month",
            "copy_fields": {
                "record_id": "record_id",
                "pid_type": "pid_type",
                "pid_value": "pid_value",
            },
            "metric_fields": {
                "unique_count": (
                    "cardinality",
                    "unique_session_id",
                    {"precision_threshold": 1000},
                ),
            },
        },
    },
}


STATS_QUERIES = {
    "bucket-file-download-histogram": {
        "cls": DateHistogramQuery,
        "params": {
            "index": "stats-file-download",
            "copy_fields": {"file": "file"},
            "query_modifiers": [filter_by_reportnumber],
            "required_filters": {
                "file": "file",
            },
        },
    },
    # "bucket-file-download-total": {
    #     "cls": TermsQuery,
    #     "params": {
    #         "index": "stats-file-download",
    #         "required_filters": {
    #             "bucket_id": "bucket_id",
    #         },
    #         "aggregated_fields": ["file_key"],
    #     },
    # },
    "record-view-total": {
        "cls": TermsQuery,
        "params": {
            "index": "stats-record-view",
            "required_filters": {
                "recid": "pid_value",
            },
            "aggregated_fields": ["pid_value"],
            "metric_fields": {
                "views": ("sum", "count", {}),
                "unique_views": ("sum", "unique_count", {}),
            },
        },
    },
}

# STATS_PERMISSION_FACTORY = TODO

STATS_REGISTER_INDEX_TEMPLATES = True

# Legacy host Elasticsearch
LEGACY_STATS_ELASTIC_HOST = "127.0.0.1"
# Legacy port Elasticsearch
LEGACY_STATS_ELASTIC_PORT = 9199
# Default port Elasticsearch

###############################################################################
# LOG USER ACTIVITY
###############################################################################

# flag to enable or disable user actions logging
LOG_USER_ACTIONS_ENABLED = True
# endpoints for logging user actions
LOG_USER_ACTIONS_ENDPOINTS = {
    "base_url": "/api/stats/",
    "page_view": "{base_url}{recid}/pageview",
    "media_view": "{base_url}{recid}/media-record-view",
    "media_download": "{base_url}{recid}/media-file-download",
}

###############################################################################
# Accounts
###############################################################################

#: Redis session storage URL.
ACCOUNTS_SESSION_REDIS_URL = "redis://localhost:6379/1"

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
    "json": dict(
        title="JSON",
        mimetype="application/json",
        serializer="invenio_records_rest.serializers:json_v1",
    ),
    "smil": dict(
        title="SMIL",
        mimetype="application/smil",
        serializer="cds.modules.records.serializers:smil_v1",
    ),
    "vtt": dict(
        title="VTT",
        mimetype="text/vtt",
        serializer="cds.modules.records.serializers:vtt_v1",
    ),
    "drupal": dict(
        title="Drupal",
        mimetype="x-application/drupal",
        serializer="cds.modules.records.serializers:drupal_v1",
    ),
    "dcite": dict(
        title="Datacite XML v3.1",
        mimetype="application/x-datacite+xml",
        serializer="cds.modules.records.serializers:datacite_v31",
    ),
}

CDS_RECORDS_UI_LINKS_FORMAT = "https://videos.cern.ch/record/{recid}"

# Endpoints for records.
RECORDS_UI_ENDPOINTS = dict(
    recid=dict(
        pid_type="recid",
        route="/record/<pid_value>",
        template="cds_records/record_detail.html",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    recid_stats=dict(
        pid_type="recid",
        route="/record/<pid_value>/stats",
        template="cds_records/record_stats.html",
        view_imp="cds.modules.records.views.stats_recid",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    recid_preview=dict(
        pid_type="recid",
        route="/record/<pid_value>/preview/<filename>",
        view_imp="cds.modules.previewer.views.preview_recid",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    recid_embed=dict(
        pid_type="recid",
        route="/record/<pid_value>/embed/<filename>",
        view_imp="cds.modules.previewer.views.preview_recid_embed",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    recid_embed_default=dict(
        pid_type="recid",
        route="/record/<pid_value>/embed",
        view_imp="cds.modules.previewer.views.preview_recid_embed",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    recid_files=dict(
        pid_type="recid",
        route="/record/<pid_value>/files/<filename>",
        view_imp="invenio_records_files.utils:file_download_ui",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    video_preview=dict(
        pid_type="depid",
        route="/deposit/<pid_value>/preview/video/<filename>",
        view_imp="cds.modules.previewer.views.preview_depid",
        record_class="cds.modules.deposit.api:Video",
    ),
    project_preview=dict(
        pid_type="depid",
        route="/deposit/<pid_value>/preview/project/<filename>",
        view_imp="cds.modules.previewer.views.preview_depid",
        record_class="cds.modules.deposit.api:Project",
    ),
    recid_export=dict(
        pid_type="recid",
        route="/record/<pid_value>/export/<any({0}):format>".format(
            ", ".join(list(CDS_RECORDS_EXPORTFORMATS.keys()))
        ),
        template="cds_records/record_export.html",
        view_imp="cds.modules.records.views.records_ui_export",
        record_class="cds.modules.records.api:CDSRecord",
    ),
    record_delete=dict(
        pid_type="recid",
        route="/record/<pid_value>/admin/delete",
        view_imp="cds.modules.records.views.records_ui_delete",
        record_class="cds.modules.records.api:CDSRecord",
        permission_factory_imp="cds.modules.records.permissions:record_delete_permission_factory",
        methods=["GET", "POST"],
    ),
)

# Endpoint for record ui.
RECORDS_UI_ENDPOINT = "{scheme}://{host}/record/{pid_value}"

# OAI Server.
OAISERVER_ID_PREFIX = "oai:cds.cern.ch:"
# Relative URL to XSL Stylesheet, placed under `modules/records/static`.
OAISERVER_XSL_URL = "/static/xsl/oai2.xsl"
OAISERVER_RECORD_INDEX = "records"

# 404 template.
RECORDS_UI_TOMBSTONE_TEMPLATE = "invenio_records_ui/tombstone.html"

CDS_RECORDS_RELATED_QUERY = "/api/records/?size=3&sort=mostrecent&q=%s"

# Endpoints for record API.
_Record_PID = 'pid(recid, record_class="cds.modules.records.api:CDSRecord")'
_Category_PID = 'pid(catid, record_class="cds.modules.records.api:Category")'
_Keyword_PID = 'pid(kwid, record_class="cds.modules.records.api:Keyword")'
RECORDS_REST_ENDPOINTS = dict(
    recid=dict(
        pid_type="recid",
        pid_minter="cds_recid",
        pid_fetcher="cds_recid",
        indexer_class=CDSRecordIndexer,
        search_class=RecordVideosSearch,
        search_factory_imp="invenio_records_rest.query.es_search_factory",
        record_serializers={
            "application/json": ("cds.modules.records.serializers" ":json_v1_response"),
            "application/smil": ("cds.modules.records.serializers" ":smil_v1_response"),
            "text/vtt": ("cds.modules.records.serializers" ":vtt_v1_response"),
            "x-application/drupal": (
                "cds.modules.records.serializers" ":drupal_v1_response"
            ),
            "application/x-datacite+xml": (
                "cds.modules.records.serializers.datacite_v31_response"
            ),
        },
        record_serializers_aliases={
            "json": "application/json",
            "smil": "application/smil",
            "vtt": "text/vtt",
            "drupal": "x-application/drupal",
            "dcite": "application/x-datacite+xml",
        },
        search_serializers={
            "application/json": ("cds.modules.records.serializers" ":json_v1_search"),
        },
        list_route="/records/",
        item_route="/record/<{0}:pid_value>".format(_Record_PID),
        default_media_type="application/json",
        max_result_window=10000,
        read_permission_factory_imp=record_read_permission_factory,
        links_factory_imp="cds.modules.records.links.record_link_factory",
    ),
    catid=dict(
        default_endpoint_prefix=True,
        pid_type="catid",
        pid_minter="cds_catid",
        pid_fetcher="cds_catid",
        indexer_class=CDSRecordIndexer,
        search_index="categories",
        search_class=RecordVideosSearch,
        search_factory_imp="invenio_records_rest.query.es_search_factory",
        record_serializers={
            "application/json": (
                "invenio_records_rest.serializers" ":json_v1_response"
            ),
        },
        search_serializers={
            "application/json": ("invenio_records_rest.serializers" ":json_v1_search"),
        },
        list_route="/categories/",
        item_route="/categories/<{0}:pid_value>".format(_Category_PID),
        default_media_type="application/json",
        max_result_window=10000,
        suggesters={
            "suggest-name": {
                "completion": {
                    "field": "suggest_name",
                }
            }
        },
        read_permission_factory_imp=record_read_permission_factory,
    ),
    kwid=dict(
        default_endpoint_prefix=True,
        pid_type="kwid",
        pid_minter="cds_kwid",
        pid_fetcher="cds_kwid",
        indexer_class=CDSRecordIndexer,
        search_index="keywords",
        search_class=NotDeletedKeywordSearch,
        search_factory_imp="invenio_records_rest.query.es_search_factory",
        record_serializers={
            "application/json": (
                "invenio_records_rest.serializers" ":json_v1_response"
            ),
        },
        search_serializers={
            "application/json": ("invenio_records_rest.serializers" ":json_v1_search"),
        },
        list_route="/keywords/",
        item_route="/keywords/<{0}:pid_value>".format(_Keyword_PID),
        default_media_type="application/json",
        max_result_window=10000,
        suggesters={
            "suggest-name": {
                "completion": {
                    "field": "suggest_name",
                }
            }
        },
        read_permission_factory_imp=record_read_permission_factory,
    ),
)

RECORDS_REST_ENDPOINTS.update(OPENDEFINITION_REST_ENDPOINTS)
# Query arg name to be able to export records in the specified format
REST_MIMETYPE_QUERY_ARG_NAME = "format"

# Sort options records REST API.
RECORDS_REST_SORT_OPTIONS = {
    "records-videos-video": {
        "bestmatch": {
            "title": "Best match",
            "fields": ["-_score"],
            "default_order": "asc",
            "order": 1,
        },
        "mostrecent": {
            "title": "Newest",
            "fields": ["-date"],
            "default_order": "asc",
            "order": 2,
        },
        "oldest": {
            "title": "Oldest",
            "fields": ["date"],
            "default_order": "asc",
            "order": 3,
        },
        "title_asc": {
            "title": "Title [Asc]",
            "fields": ["title.title"],
            "default_order": "asc",
            "order": 4,
        },
        "title_desc": {
            "title": "Title [Desc]",
            "fields": ["title.title"],
            "default_order": "desc",
            "order": 5,
        },
    }
}

# Default sort for records REST API.
RECORDS_REST_DEFAULT_SORT = {
    "records-videos-video": {
        "query": "bestmatch",
        "noquery": "mostrecent",
    },
    "deposits-records-videos-project": {
        "query": "bestmatch",
        "noquery": "mostrecent_created",
    },
}

# Defined facets for records REST API.
RECORDS_REST_FACETS = dict()

# This is required because of elasticsearch 2.1 error response.
# From 2.2 this is not needed.
RECORDS_REST_ELASTICSEARCH_ERROR_HANDLERS = {
    "query_parsing_exception": (
        "invenio_records_rest.views" ":elasticsearch_query_parsing_exception_handler"
    ),
    "token_mgr_error": (
        "invenio_records_rest.views" ":elasticsearch_query_parsing_exception_handler"
    ),
}

RECORD_UI_ENDPOINT = "{scheme}://{host}/record/{pid_value}"

# Facets for the specific index
DEPOSIT_PROJECT_FACETS = {
    "deposits-records-videos-project": {
        "aggs": {
            "project_status": {
                "terms": {"field": "_deposit.status"},
            },
            "category": {
                "terms": {"field": "category.untouched"},
            },
            "task_transcode": {
                "terms": {"field": "_cds.state.file_transcode.keyword"},
            },
            "task_extract_frames": {
                "terms": {"field": "_cds.state.file_video_extract_frames.keyword"},
            },
            "created_by": created_by_me_aggs,
        },
        "filters": {
            "project_status": terms_filter("_deposit.status"),
            "category": terms_filter("category.untouched"),
            "task_transcode": terms_filter("_cds.state.file_transcode.keyword"),
            "task_extract_frames": terms_filter(
                "_cds.state.file_video_extract_frames.keyword"
            ),
            "created_by": terms_filter("_deposit.created_by"),
        },
    },
}

RECORD_VIDEOS_FACETS = {
    "records-videos-video": {
        "aggs": {
            "category": {
                "terms": {"field": "category.untouched"},
            },
            "type": {
                "terms": {"field": "type.untouched"},
            },
            "language": {
                "terms": {"field": "language.untouched"},
            },
            "years": {
                "date_histogram": {
                    "field": "date",
                    "interval": "year",
                    "format": "yyyy",
                }
            },
        },
        "filters": {
            "press": lowercase_filter("Press"),
            "keyword": lowercase_filter("keywords.name"),
            "category": terms_filter("category.untouched"),
            "type": terms_filter("type.untouched"),
            "language": terms_filter("language"),
            "years": range_filter("date", format="yyyy", end_date_math="/y"),
        },
    }
}

# Deposit search index.
DEPOSIT_UI_SEARCH_INDEX = "deposits-records-videos-project"

# Options for sorting deposits.
DEPOSIT_REST_SORT_OPTIONS = {
    "deposits-records-videos-project": dict(
        bestmatch=dict(
            fields=["-_score"],
            title="Best match",
            default_order="asc",
            order=1,
        ),
        mostrecent_created=dict(
            fields=["-_created"],
            title="Newest Created",
            default_order="asc",
            order=2,
        ),
        oldest_created=dict(
            fields=["_created"],
            title="Oldest Created",
            default_order="asc",
            order=3,
        ),
        mostrecent_updated=dict(
            fields=["-_updated"],
            title="Newest Updated",
            default_order="asc",
            order=4,
        ),
        oldest_updated=dict(
            fields=["_updated"],
            title="Oldest Updated",
            default_order="asc",
            order=5,
        ),
        title_asc=dict(
            fields=["title.title.raw"],
            title="Title [Asc]",
            default_order="asc",
            order=6,
        ),
        title_desc=dict(
            fields=["title.title.raw"],
            title="Title [Desc]",
            default_order="desc",
            order=7,
        ),
    ),
}

DEPOSIT_REST_DEFAULT_SORT = {
    "deposits-records-videos-project": {
        "query": "bestmatch",
        "noquery": "mostrecent_created",
    }
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

RECORDS_UI_DEFAULT_PERMISSION_FACTORY = (
    "cds.modules.records.permissions:deposit_read_permission_factory"
)

#: Standard record removal reasons.
CDS_REMOVAL_REASONS = [
    ("", ""),
    ("spam", "Spam record, removed by CDS staff."),
    ("uploader", "Record removed on request by uploader."),
    ("takedown", "Record removed on request by third-party."),
]

###############################################################################
# Files
###############################################################################
FILES_REST_PERMISSION_FACTORY = (
    "cds.modules.records.permissions:files_permission_factory"
)

# Files storage
FIXTURES_FILES_LOCATION = os.environ.get("APP_FIXTURES_FILES_LOCATION", "/tmp")

###############################################################################
# Formatter
###############################################################################
#: List of allowed titles in badges.
FORMATTER_BADGES_ALLOWED_TITLES = ["DOI", "doi", "RN", "rn"]

#: Mapping of titles.
FORMATTER_BADGES_TITLE_MAPPING = {"doi": "DOI", "rn": "RN"}

# Enable badges
FORMATTER_BADGES_ENABLE = True

###############################################################################
# Home page
###############################################################################

# Display a homepage.
FRONTPAGE_ENDPOINT = "cds_home.index"
# Featured query
FRONTPAGE_FEATURED_QUERY = "/api/records/?q=featured:true&size=1&sort=mostrecent"
# Recent videos query
FRONTPAGE_RECENT_QUERY = "/api/records/?size=3&sort=mostrecent&type=VIDEO"
# Queries for the boxes
FRONTPAGE_QUERIES = [
    {"size": 5, "page": 1},
    {"size": 5, "page": 1},
    {"size": 5, "page": 1},
]
# Quote before search box
FRONTPAGE_SLOGAN = "Search for over than 1.000.000 records"
# Keywords to use when searching in ES keywords.name
FRONTPAGE_CHANNELS = [
    {
        "label": "Press",
        # https://github.com/CERNDocumentServer/cds-videos/issues/1759
        "img_filename": "channel_press.jpg",
        "qs": "press=videos",
    },
    {
        "label": "Accelerators",
        # https://mediaarchive.cern.ch/MediaArchive/Video/Public/Footage/CERN/
        # 2008/CERN-FOOTAGE-2008-022/CERN-FOOTAGE-2008-022-001/
        # CERN-FOOTAGE-2008-022-001-posterframe-640x360-at-25-percent.jpg
        "img_filename": "channel_accelerators.jpg",
        "qs": "keyword=accelerator",
    },
    {
        "label": "Physics",
        # https://mediaarchive.cern.ch/MediaArchive/Video/Public/Movies/CERN/
        # 2015/CERN-MOVIE-2015-025/CERN-MOVIE-2015-025-011/
        # CERN-MOVIE-2015-025-011-posterframe-640x360-at-5-percent.jpg
        "img_filename": "channel_physics.jpg",
        "qs": "keyword=physics",
    },
    {
        "label": "Experiments",
        # https://mediaarchive.cern.ch/MediaArchive/Video/Public/Movies/CERN/
        # 2016/CERN-MOVIE-2016-031/CERN-MOVIE-2016-031-003/
        # CERN-MOVIE-2016-031-003-posterframe-640x360-at-5-percent.jpg
        "img_filename": "channel_experiments.jpg",
        "qs": "keyword=experiment",
    },
    {
        "label": "Data",
        # https://mediaarchive.cern.ch/MediaArchive/Video/Public/Movies/CERN/
        # 2016/CERN-MOVIE-2016-077/CERN-MOVIE-2016-077-004/
        # CERN-MOVIE-2016-077-004-posterframe-640x360-at-5-percent.jpg
        "img_filename": "channel_data.jpg",
        "qs": "keyword=data",
    },
    {
        "label": "Animations",
        # https://github.com/CERNDocumentServer/cds-videos/issues/1759
        "img_filename": "channel_animations.jpg",
        "qs": "keyword=animations",
    },
]

FRONTPAGE_TREND_TOPICS = [
    {
        "label": "Antimatter",
        "qs": "keyword=antimatter",
    },
    {
        "label": "Dark Matter",
        "qs": 'q=keywords.name:"dark matter"',
    },
    {
        "label": "Higgs",
        "qs": "keyword=higgs",
    },
    {
        "label": "HL-LHC",
        "qs": 'q=keywords.name:"HL-LHC"',
    },
    {
        "label": "LHC",
        "qs": "keyword=LHC",
    },
    {
        "label": "CLOUD",
        "qs": "keyword=CLOUD",
    },
    {
        "label": "FCC",
        "qs": "keyword=FCC",
    },
    {
        "label": "AWAKE",
        "qs": "keyword=AWAKE",
    },
    {
        "label": "Collisions",
        "qs": "keyword=collisions",
    },
    {
        "label": "History",
        "qs": "keyword=history",
    },
    {
        "label": "Video News Releases",
        "qs": 'q=keywords.name:"VNR" OR keywords.name:"video news release"',
    },
]

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
SECURITY_LOGIN_USER_TEMPLATE = "cds_theme/login_user.html"

# Security login salt.
SECURITY_LOGIN_SALT = "CHANGE_ME"

# Force single hash
SECURITY_PASSWORD_SINGLE_HASH = True

# Flask configuration
# ===================
# See details on
# http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values

APP_ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
APP_DEFAULT_SECURE_HEADERS["content_security_policy"] = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "https://*.theoplayer.com",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://www.dropbox.com",
    ],
    "style-src": [
        "'self'",
        "https://*.theoplayer.com",
        "https://*.cern.ch/",
        "'unsafe-inline'",
    ],
    "img-src": ["'self'", "https://*.theoplayer.com", "data:"],
    "connect-src": ["'self'", "https://*.theoplayer.com", "https://*.cern.ch"],
    "object-src": ["'self'"],
    "media-src": ["'self'", "blob:"],
    "frame-src": ["'self'", "https://*.theoplayer.com"],
    "child-src": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'self'"],
    "base-uri": ["'self'"],
    "worker-src": ["'self'", "blob:"],
    "manifest-src": ["'none'"],
    # "prefetch-src": ["'none'"],
    "font-src": [
        "'self'",
        "data:",
        "https://fonts.gstatic.com",
        "https://fonts.googleapis.com",
        "https://*.cern.ch/",
    ],
}
SITE_URL = "https://127.0.0.1:5000"

###############################################################################
# User Profiles
###############################################################################

# Override profile template.
USERPROFILES_PROFILE_TEMPLATE = "cds_theme/profile.html"
USERPROFILES_EMAIL_ENABLED = False
# This is needed to ensure the correct template for profile page.
SETTINGS_TEMPLATE = "invenio_theme/page_settings.html"

###############################################################################
# OAuth
###############################################################################

OAUTHCLIENT_CERN_OPENID_USERINFO_URL = os.environ.get(
    "OAUTHCLIENT_CERN_OPENID_USERINFO_URL",
    "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/userinfo",
)

OAUTHCLIENT_CERN_OPENID_ALLOWED_ROLES = ["cern-user"]

OAUTHCLIENT_CERN_OPENID_REFRESH_TIMEDELTA = timedelta(minutes=-5)
"""Default interval for refreshing CERN extra data (e.g. groups).

False value disabled the refresh.
"""

OAUTHCLIENT_CERN_OPENID_SESSION_KEY = "identity.cdsvideos_openid_provides"
"""Name of session key where CERN roles are stored."""

REMOTE_APP_NAME = "cern_openid"

REMOTE_APP = dict(
    title="CERN",
    description="Connecting to CERN Organization.",
    icon="",
    logout_url=os.environ.get(
        "OAUTH_CERN_OPENID_LOGOUT_URL",
        "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/logout",
    ),
    params=dict(
        base_url=os.environ.get(
            "OAUTH_CERN_OPENID_BASE_URL", "https://auth.cern.ch/auth/realms/cern"
        ),
        request_token_params={"scope": "openid"},
        access_token_url=os.environ.get(
            "OAUTH_CERN_OPENID_ACCESS_TOKEN_URL",
            "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token",
        ),
        access_token_method="POST",
        authorize_url=os.environ.get(
            "OAUTH_CERN_OPENID_AUTHORIZE_URL",
            "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/auth",
        ),
        app_key="CERN_APP_OPENID_CREDENTIALS",
        content_type="application/json",
    ),
    authorized_handler="invenio_oauthclient.handlers:authorized_signup_handler",
    disconnect_handler="cds.modules.oauthclient.cern_openid:disconnect_handler",
    signup_handler=dict(
        info="cds.modules.oauthclient.cern_openid:account_info",
        setup="cds.modules.oauthclient.cern_openid:account_setup",
        view="invenio_oauthclient.handlers:signup_handler",
    ),
)

OAUTHCLIENT_REMOTE_APPS = dict(cern_openid=REMOTE_APP)
"""CERN Openid Remote Application."""


OAUTHCLIENT_CERN_OPENID_JWT_TOKEN_DECODE_PARAMS = dict(
    options=dict(
        verify_signature=False,
        verify_aud=False,
    ),
    algorithms=["HS256", "RS256"],
)

#: Credentials for CERN OAuth (must be changed to work).
CERN_APP_OPENID_CREDENTIALS = dict(
    consumer_key=os.environ.get("OAUTH_CERN_CONSUMER_KEY", "changeme"),
    consumer_secret=os.environ.get("OAUTH_CERN_CONSUMER_SECRET", "changeme"),
)

## Needed for populating the user profiles when users login via CERN Openid
USERPROFILES_EXTEND_SECURITY_FORMS = True

# Set the template
OAUTH2SERVER_SETTINGS_TEMPLATE = "cds_theme/settings.html"

###############################################################################
# Theme
###############################################################################

# The site name
THEME_SITENAME = _("CDS Videos · CERN")
THEME_SITEDESCRIPTION = _(
    "CDS Videos is the CERN official repository to " "archive and disseminate videos."
)
# Default site URL (used only when not in a context - e.g. like celery tasks).
THEME_SITEURL = "http://127.0.0.1:5000"
# The theme logo.
THEME_LOGO = False
# The base template.
BASE_TEMPLATE = "cds_theme/page.html"
# Header template for entire site.
HEADER_TEMPLATE = "cds_theme/header.html"
# Endpoint for breadcrumb root.
THEME_BREADCRUMB_ROOT_ENDPOINT = "cds_home.index"
# Cover template
COVER_TEMPLATE = "cds_theme/page_cover.html"
# 404 Error
THEME_404_TEMPLATE = "cds_theme/error/404.html"
# 500 Error
THEME_500_TEMPLATE = "cds_theme/error/500.html"
# Error template
THEME_ERROR_TEMPLATE = "cds_theme/error/base.html"
# Tracking template
THEME_TRACKINGCODE_TEMPLATE = "cds_theme/trackingcode.html"
# Piwik tracking code: set None to disabled it
THEME_PIWIK_ID = None

###############################################################################
# Previewer
###############################################################################

# Base CSS bundle to include in all previewers
PREVIEWER_BASE_CSS_BUNDLES = ["cds_main_theme"]
# Base JS bundle to include in all previewers
PREVIEWER_BASE_JS_BUNDLES = ["cds_main_app"]
# Decides which previewers are available and their priority.
PREVIEWER_PREFERENCE = [
    "csv_dthreejs",
    "simple_image",
    "json_prismjs",
    "xml_prismjs",
    "mistune",
    "pdfjs",
    "ipynb",
    "cds_video",
    "cds_embed_video",
    "zip",
    "cds_deposit_video",
]
# Previewer base template
PREVIEWER_BASE_TEMPLATE = "cds_previewer/base.html"
# Licence key and base URL for THEO player
THEOPLAYER_LIBRARY_LOCATION = None
THEOPLAYER_LICENSE = None
# Wowza server URL for m3u8 playlist generation
WOWZA_PLAYLIST_URL = (
    "https://wowza.cern.ch/cds/_definist_/smil:" "{filepath}/playlist.m3u8"
)
WOWZA_VIDEO_URL = "https://wowza.cern.ch/cds/_definist_/mp4:%s/playlist.m3u8"
# Size
VIDEO_POSTER_SIZE = (180, 101)
# File system location of videos
VIDEOS_LOCATION = "/eos/media/cds/test/videos/files/"
# XRootD prefix for videos
VIDEOS_XROOTD_ENDPOINT = "root://eosmedia.cern.ch/"
# Ex. root://eosmedia.cern.ch//eos/media/cds/test/videos/files/
VIDEOS_XROOTD_PREFIX = "{endpoint}{location}".format(
    endpoint=VIDEOS_XROOTD_ENDPOINT, location=VIDEOS_LOCATION
)
# EOS path for video library `e-groups`
VIDEOS_EOS_PATH_EGROUPS = ["vmo-restictedrights@cern.ch"]
"""
By default, this field is hidden and disabled. It becomes visible only to
the users that are part of the e-groups in VIDEOS_EOS_PATH_EGROUPS and admins.
"""

###############################################################################
# JSON Schemas
###############################################################################

JSONSCHEMAS_ENDPOINT = "/schemas"
JSONSCHEMAS_HOST = os.environ.get("JSONSCHEMAS_HOST", "127.0.0.1:5000")
JSONSCHEMAS_URL_SCHEME = "https"

###############################################################################
# Indexer
###############################################################################

INDEXER_DEFAULT_INDEX = "records-default-v1.0.0"
INDEXER_DEFAULT_DOC_TYPE = "default-v1.0.0"
INDEXER_BULK_REQUEST_TIMEOUT = 60

###############################################################################
# Deposit
###############################################################################
#: DOI prefixes considered as local prefixes.
CDS_LOCAL_DOI_PREFIXES = ["10.5072", "10.17181"]

#: DataCite API - Prefix for minting DOIs in (10.5072 is a test prefix).
PIDSTORE_DATACITE_DOI_PREFIX = "10.5072"
# PID minter used for record submissions.
DEPOSIT_PID_MINTER = "cds_recid"
#: Enable the DataCite minding of DOIs after Deposit publishing
DEPOSIT_DATACITE_MINTING_ENABLED = False

# Template for deposit list view.
DEPOSIT_UI_INDEX_TEMPLATE = "cds_deposit/index.html"
# Template to use for UI.
DEPOSIT_UI_NEW_TEMPLATE = "cds_deposit/edit.html"
# The schema form deposit
DEPOSIT_DEFAULT_SCHEMAFORM = "json/cds_deposit/forms/project.json"
# Default schema for the deposit
DEPOSIT_DEFAULT_JSONSCHEMA = "deposits/records/videos/project/project-v1.0.0.json"
# Deposit schemas
DEPOSIT_JSONSCHEMA = {
    "project": "deposits/records/videos/project/project-v1.0.0.json",
    "video": "deposits/records/videos/video/video-v1.0.0.json",
}
# Template for <invenio-records-form> directive
DEPOSIT_UI_JSTEMPLATE_FORM = "templates/cds_deposit/form.html"
DEPOSIT_UI_JSTEMPLATE_ACTIONS = "templates/cds_deposit/actions.html"
DEPOSIT_SEARCH_API = "/api/deposits/project/"
_CDSDeposit_PID = 'pid(depid,record_class="cds.modules.deposit.api:CDSDeposit")'
_Project_PID = 'pid(depid,record_class="cds.modules.deposit.api:Project")'
_Video_PID = 'pid(depid,record_class="cds.modules.deposit.api:Video")'
DEPOSIT_UI_ENDPOINT_DEFAULT = "{scheme}://{host}/deposit/{pid_value}"
DEPOSIT_UI_ENDPOINT = "{scheme}://{host}/deposit/{type}/{pid_value}"
DEPOSIT_RECORDS_API_DEFAULT = "/api/deposits/{pid_value}"
DEPOSIT_RECORDS_API = "/api/deposits/{type}/{pid_value}"

# Deposit rest endpoints
DEPOSIT_REST_ENDPOINTS = dict(
    depid=dict(
        pid_type="depid",
        pid_minter="deposit",
        pid_fetcher="deposit",
        default_endpoint_prefix=True,
        record_class="cds.modules.deposit.api:CDSDeposit",
        files_serializers={
            "application/json": (
                "cds.modules.invenio_deposit.serializers" ":json_v1_files_response"
            ),
        },
        record_serializers={
            "application/json": (
                "invenio_records_rest.serializers" ":json_v1_response"
            ),
        },
        search_class="cds.modules.invenio_deposit.search:DepositSearch",
        search_serializers={
            "application/json": ("invenio_records_rest.serializers" ":json_v1_search"),
        },
        list_route="/deposits/",
        indexer_class=CDSRecordIndexer,
        item_route="/deposits/<{0}:pid_value>".format(_CDSDeposit_PID),
        file_list_route="/deposits/<{0}:pid_value>/files".format(_CDSDeposit_PID),
        file_item_route="/deposits/<{0}:pid_value>/files/<path:key>".format(
            _CDSDeposit_PID
        ),
        default_media_type="application/json",
        links_factory_imp="cds.modules.deposit.links:deposit_links_factory",
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(record=record).can(),
            write_scope.id,
        ),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: record_update_permission_factory(record=record).can(),
            write_scope.id,
        ),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(record=record).can(),
            write_scope.id,
        ),
        max_result_window=10000,
    ),
    project=dict(
        pid_type="depid",
        pid_minter="deposit",
        pid_fetcher="deposit",
        default_endpoint_prefix=False,
        record_class="cds.modules.deposit.api:Project",
        search_factory_imp="cds.modules.deposit.search:deposit_search_factory",
        record_loaders={
            "application/json": "cds.modules.deposit.loaders:project_loader",
            "application/vnd.project.partial+json": "cds.modules.deposit.loaders:partial_project_loader",
        },
        files_serializers={
            "application/json": (
                "cds.modules.invenio_deposit.serializers" ":json_v1_files_response"
            ),
        },
        record_serializers={
            "application/json": (
                "cds.modules.records.serializers" ":cdsdeposit_json_v1_response"
            ),
            "application/vnd.project.partial+json": (
                "cds.modules.records.serializers" ":cdsdeposit_json_v1_response"
            ),
        },
        search_class="cds.modules.deposit.search:DepositVideosSearch",
        search_serializers={
            "application/json": ("invenio_records_rest.serializers" ":json_v1_search"),
        },
        list_route="/deposits/project/",
        indexer_class=CDSRecordIndexer,
        item_route="/deposits/project/<{0}:pid_value>".format(_Project_PID),
        file_list_route="/deposits/project/<{0}:pid_value>/files".format(_Project_PID),
        file_item_route="/deposits/project/<{0}:pid_value>/files/<path:key>".format(
            _Project_PID
        ),
        default_media_type="application/json",
        links_factory_imp="cds.modules.deposit.links:project_links_factory",
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(record=record).can(),
            write_scope.id,
        ),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_update_permission_factory(record=record).can(),
            write_scope.id,
        ),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(record=record).can(),
            write_scope.id,
        ),
        max_result_window=10000,
    ),
    video=dict(
        pid_type="depid",
        pid_minter="deposit",
        pid_fetcher="deposit",
        default_endpoint_prefix=False,
        record_class="cds.modules.deposit.api:Video",
        record_loaders={
            "application/json": "cds.modules.deposit.loaders:video_loader",
            "application/vnd.video.partial+json": "cds.modules.deposit.loaders:partial_video_loader",
        },
        files_serializers={
            "application/json": (
                "cds.modules.invenio_deposit.serializers" ":json_v1_files_response"
            ),
        },
        record_serializers={
            "application/json": (
                "cds.modules.records.serializers" ":cdsdeposit_json_v1_response"
            ),
            "application/vnd.video.partial+json": (
                "cds.modules.records.serializers" ":cdsdeposit_json_v1_response"
            ),
        },
        search_class="cds.modules.invenio_deposit.search:DepositSearch",
        search_serializers={
            "application/json": ("invenio_records_rest.serializers" ":json_v1_search"),
        },
        list_route="/deposits/video/",
        indexer_class=CDSRecordIndexer,
        item_route="/deposits/video/<{0}:pid_value>".format(_Video_PID),
        file_list_route="/deposits/video/<{0}:pid_value>/files".format(_Video_PID),
        file_item_route="/deposits/video/<{0}:pid_value>/files/<path:key>".format(
            _Video_PID
        ),
        default_media_type="application/json",
        links_factory_imp="cds.modules.deposit.links:video_links_factory",
        create_permission_factory_imp=check_oauth2_scope(
            lambda record: record_create_permission_factory(record=record).can(),
            write_scope.id,
        ),
        read_permission_factory_imp=deposit_read_permission_factory,
        update_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_update_permission_factory(record=record).can(),
            write_scope.id,
        ),
        delete_permission_factory_imp=check_oauth2_scope(
            lambda record: deposit_delete_permission_factory(record=record).can(),
            write_scope.id,
        ),
        max_result_window=10000,
    ),
)

DEPOSIT_PROJECT_UI_ENDPOINT = "{scheme}://{host}/deposit/project/{pid_value}"

# Deposit UI endpoints
DEPOSIT_RECORDS_UI_ENDPOINTS = {
    "video_new": {
        "pid_type": "depid",
        "route": "/deposit/video/new",
        "template": "cds_deposit/edit.html",
        "record_class": "cds.modules.deposit.api:CDSDeposit",
    },
    "depid": {
        "pid_type": "depid",
        "route": "/deposit/<pid_value>",
        "template": "cds_deposit/edit.html",
        "record_class": "cds.modules.deposit.api:CDSDeposit",
    },
    "project": {
        "pid_type": "depid",
        "route": "/deposit/project/<pid_value>",
        "template": "cds_deposit/edit.html",
        "record_class": "cds.modules.deposit.api:Project",
        "view_imp": "cds.modules.deposit.views:project_view",
    },
}
# Deposit successful messages
DEPOSIT_RESPONSE_MESSAGES = dict(
    self=dict(message="Saved successfully."),
    delete=dict(message="Deleted succesfully."),
    discard=dict(message="Changes discarded succesfully."),
    publish=dict(message="Published succesfully."),
    edit=dict(message="Edited succesfully."),
)

DEPOSIT_FORM_TEMPLATES_BASE = "templates/cds_deposit/angular-schema-form"
DEPOSIT_FORM_TEMPLATES = {
    # "default": "default.html",
    "fieldset": "fieldset.html",
    "ckeditor": "textarea.html",
    "uiselect": "uiselect.html",
    "array": "array.html",
    "radios_inline": "radios_inline.html",
    "radios": "radios.html",
    "select": "select.html",
    "button": "button.html",
    "textarea": "textarea.html",
    "checkbox": "checkbox.html",
    "uiselectmultiple": "uiselectmultiple.html",
    "strapselect": "strapselect.html",
}

# App key for uploading files from dropbox
DEPOSIT_DROPBOX_APP_KEY = "CHANGE_ME"

# Default copyright holder & url
DEPOSIT_AVC_COPYRIGHT = {
    "holder": "CERN",
    "url": "http://copyright.web.cern.ch",
}

# The number of max videos per project. It blocks the upload of new videos in a
# project only client side
DEPOSIT_PROJECT_MAX_N_VIDEOS = 10

###############################################################################
# Keywords
###############################################################################
CDS_KEYWORDS_HARVESTER_URL = "http://home.cern/api/tags-json-feed"

# OpenDefinition
# ==============
#: Hostname for OpenAIRE's grant resolver.
OPENDEFINITION_JSONRESOLVER_HOST = "cds.cern.ch"

###############################################################################
# ffmpeg
###############################################################################

CDS_FFMPEG_METADATA_ALIASES = {
    "streams/0/title": [
        "format/tags/title",
        "format/tags/com.apple.quicktime.title",
    ],
    "streams/0/description": [
        "format/tags/description",
        "format/tags/com.apple.quicktime.description",
    ],
    "streams/0/keywords": ["format/tags/com.apple.quicktime.keywords"],
    "streams/0/creation_time": ["format/tags/creation_time"],
}
CDS_FFMPEG_METADATA_POST_SPLIT = ["streams/0/keywords"]


###############################################################################
# OPENCAST
###############################################################################

CDS_OPENCAST_QUALITIES = {
    "360p": {
        "width": 640,
        "height": 360,
        "audio_bitrate": 32,
        "video_bitrate": 836,
        "frame_rate": 25,
        "smil": True,
        "opencast_publication_tag": "360p-quality",
    },
    "480p": {
        "width": 854,
        "height": 480,
        "audio_bitrate": 32,
        "video_bitrate": 1436,
        "frame_rate": 25,
        "smil": True,
        "opencast_publication_tag": "480p-quality",
    },
    "720p": {
        "width": 1280,
        "height": 720,
        "audio_bitrate": 64,
        "video_bitrate": 2672,
        "frame_rate": 25,
        "smil": True,
        "opencast_publication_tag": "720p-quality",
    },
    "1080p": {
        "width": 1920,
        "height": 1080,
        "audio_bitrate": 96,
        "video_bitrate": 5872,
        "frame_rate": 25,
        "smil": True,
        "opencast_publication_tag": "1080p-quality",
        "tags": {
            "type": "hd",
            "download": "true",  # noqa If true subformat is displayed in the download box in the details page, if not it will be displayed as "Other video formats".
        },
    },
    "2160p": {
        "width": 3840,
        "height": 2160,
        "audio_bitrate": 96,
        "video_bitrate": 19872,
        "frame_rate": 25,
        "smil": True,
        "opencast_publication_tag": "2160p-quality",
        "tags": {
            "type": "ultra hd",
            "download": "true",
        },
    },
}
"""List of qualities available on Opencast server."""

CDS_OPENCAST_HOST = "https://changeme"
CDS_OPENCAST_API_USERNAME = "changeme"
CDS_OPENCAST_API_PASSWORD = "changeme"
CDS_OPENCAST_SERIES_ID = "changeme"
CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT = False
CDS_OPENCAST_STATUS_CHECK_TASK_TIMEOUT = 5 * 60  # 5 minutes
CDS_OPENCAST_DOWNLOAD_TASK_TIMEOUT = 30 * 60  # 30 minutes

CDS_LDAP_URL = "ldap://xldap.cern.ch"

# Sets the location to share the video files among the different tasks
CDS_FILES_TMP_FOLDER = "/tmp/videos"

# Invenio APP
APP_THEME = ["bootstrap3"]

# Invenio-Search
# ==============
SEARCH_INDEX_PREFIX = "cds-videos-prod-"

REST_CSRF_ENABLED = True

ACCOUNTS_JWT_ENABLE = False

CELERY_TASK_ALWAYS_EAGER = False
