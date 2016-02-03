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

"""cds base Invenio configuration."""

from __future__ import absolute_import, print_function

import os


# Identity function for string extraction
def _(x):
    """Indentity function."""
    return x

# Database
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://localhost/cds")
SQLALCHEMY_ECHO = False

# Default language and timezone
BABEL_DEFAULT_LANGUAGE = 'en'
BABEL_DEFAULT_TIMEZONE = 'Europe/Zurich'
I18N_LANGUAGES = []

# Distributed task queue
BROKER_URL = os.environ.get(
    "APP_BROKER_URL",
    "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "APP_CACHE_REDIS_URL",
    "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']

# Cache
CACHE_KEY_PREFIX = "cache::"
CACHE_REDIS_URL = os.environ.get(
    "APP_CACHE_REDIS_URL",
    "redis://localhost:6379/0")
CACHE_TYPE = "redis"

BASE_TEMPLATE = "cds_theme/page.html"

# Theme
THEME_SITENAME = _("CDS")

# Search
SEARCH_AUTOINDEX = []

RECORDS_UI_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        route='/record/<pid_value>',
        template='invenio_records_ui/detail.html',
    ), )

# DebugToolbar
DEBUG_TB_ENABLED = True
DEBUG_TB_INTERCEPT_REDIRECTS = False


# SASS
# FIXME: ADD npm install node-sass -g to documentation or when invenio-theme
# just remove it from here.
SASS_BIN = 'node-sass'

REQUIREJS_CONFIG = "js/cds-build.js"

# Search UI
# SEARCH_UI_SEARCH_API = 'cds.elastic'
SEARCH_UI_SEARCH_API = '/api/records/'
