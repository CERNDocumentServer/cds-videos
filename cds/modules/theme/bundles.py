# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016, 2017 CERN.
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

"""JS/CSS bundles for CDS Theme."""

from __future__ import absolute_import, print_function

from flask_assets import Bundle
from invenio_assets import NpmBundle

css = Bundle(
    Bundle(
        'node_modules/ng-dialog/css/ngDialog.css',
        'node_modules/ng-dialog/css/ngDialog-theme-default.css',
        'node_modules/ngmodal/dist/ng-modal.css',
        filters='cleancssurl',
    ),
    NpmBundle(
        'scss/cds.scss',
        filters='node-scss,cleancssurl',
        npm={
            'bootstrap-sass': '~3.3.5',
            'font-awesome': '~4.4.0',
            'ngmodal': '~2.0.1'
        }
    ),
    output='gen/cds.%(version)s.css',
)

"""Default CSS bundle."""

js = NpmBundle(
    Bundle(
        'node_modules/jquery/jquery.js',
        'node_modules/bootstrap-sass/assets/javascripts/bootstrap.js',
        'node_modules/angular/angular.js',
        'node_modules/ng-dialog/js/ngDialog.js',
        'node_modules/clipboard/dist/clipboard.js',
        'node_modules/ngclipboard/dist/ngclipboard.js',
        'node_modules/underscore/underscore.js',
        'node_modules/d3/d3.js',
        'node_modules/angular-loading-bar/build/loading-bar.js',
        'js/cds/module.js',
        'node_modules/invenio-search-js/dist/invenio-search-js.js',
        'js/main.js',
        filters='jsmin',
    ),
    depends=(
        'js/cds_deposit/avc/filters/progressClass.js',
        'js/cds_deposit/avc/filters/progressIcon.js',
        'js/*.js',
        'js/cds/*.js',
        'node_modules/invenio-search-js/dist/*.js',
    ),
    filters='jsmin',
    output='gen/cds.%(version)s.js',
    npm={
        'angular': '~1.4.7',
        'ng-dialog': '~0.6.0',
        'clipboard': '~1.5.16',
        'ngclipboard': '~1.1.1',
        'underscore': '~1.8.3',
    }
)
"""Default JavaScript bundle."""
