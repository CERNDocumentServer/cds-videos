# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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

"""JS/CSS bundles for Records."""

from __future__ import absolute_import, print_function

from flask_assets import Bundle
from invenio_assets import NpmBundle

stats_js = NpmBundle(
    'node_modules/invenio-charts-js/dist/lib.bundle.js',
    'js/cds_records/stats.js',
    output='gen/cds.records.stats.%(version)s.js',
    npm={
        'invenio-charts-js': '^0.2.2',
    }
)

stats_css = Bundle(
    Bundle(
        'node_modules/invenio-charts-js/src/styles/styles.scss',
        'scss/stats.scss',
        filters='node-scss,cleancssurl',
    ),
    output='gen/cds.stats.%(version)s.css',
)

js = NpmBundle(
    Bundle(
        'node_modules/cds/dist/cds.js',
        'node_modules/angular-sanitize/angular-sanitize.js',
        'node_modules/angular-strap/dist/angular-strap.js',
        'node_modules/invenio-files-js/dist/invenio-files-js.js',
        'node_modules/ngmodal/dist/ng-modal.js',
        'js/cds_records/main.js',
        'js/cds_records/user_actions_logger.js',
        filters='jsmin',
    ),
    depends=(
        'node_modules/cds/dist/*.js',
    ),
    filters='jsmin',
    output='gen/cds.record.%(version)s.js',
    npm={
        'angular': '~1.4.10',
        'angular-sanitize': '~1.4.10',
        'angular-loading-bar': '~0.9.0',
        'cds': '~0.2.0',
        'ng-dialog': '~0.6.0',
        'ngmodal': '~2.0.1'
    }
)
