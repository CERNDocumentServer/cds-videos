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

from invenio.base.config import PACKAGES as _PACKAGES


PACKAGES = [
    "cds.base",
    "cds.demosite",
    "cds.modules.*",
] + _PACKAGES

PACKAGES_EXCLUDE = [
    "invenio.modules.annotations",
    "invenio.modules.communities",
    "invenio.modules.pages",
]

EXTENSIONS = [
    'invenio.ext.confighacks',
    'invenio.ext.jinja2hacks',
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
    'invenio.modules.deposit.url_converters',
]


CFG_SITE_NAME = "CERN Document Server"
CFG_SITE_NAME_INTL = {
    "en": "CERN Document Server",  # Shouldn't be required.
    "fr": "CERN Document Server",
    "de": "CERN Document Server",
    "it": "CERN Document Server"
}

CFG_SITE_MISSION = "Access articles, reports and multimedia content in HEP"
CFG_SITE_MISSION_INTL = {
    "en": "Access articles, reports and multimedia content in HEP",
    "fr": "Articles, rapports et multimédia de la physique des hautes énergies",
}

CFG_SITE_LANGS = ["en", "fr", "de", "it"]

DEPOSIT_TYPES = [
    'cds.modules.deposit.workflows.talk.talk',
]

try:
    from cds.instance_config import *  # noqa
except ImportError:
    pass
