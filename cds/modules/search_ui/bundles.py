# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""JS/CSS bundles for CDS Search UI."""

from __future__ import absolute_import, print_function

from flask_assets import Bundle
from invenio_assets import NpmBundle

css = Bundle(
    'node_modules/angular-mass-autocomplete/massautocomplete.theme.css',
)

js = NpmBundle(
    'node_modules/d3/d3.js',
    'node_modules/angular-loading-bar/build/loading-bar.js',
    'node_modules/angular-mass-autocomplete/massautocomplete.js',
    'node_modules/invenio-search-js/dist/invenio-search-js.js',
    'js/invenio_search_bar_suggestions.js',
    'js/cds/suggestions.js',
    filters='jsmin',
    depends=(
        'node_modules/invenio-search-js/dist/*.js',
        'node_modules/d3/*',
    ),
    output='gen/cds.search.%(version)s.js',
    npm={
        'angular-mass-autocomplete': '~0.5.0',
        'angular-loading-bar': '~0.9.0',
        'd3': '^3.5.17',
        'invenio-search-js': '^1.5.4',
    },
)

"""Default JavaScript bundle."""
