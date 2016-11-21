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

"""UI for Invenio-Deposit."""

from flask_assets import Bundle
from invenio_assets import NpmBundle

from invenio_deposit.bundles import (
    js_dependecies_autocomplete,
    js_dependecies_uploader,
    js_dependencies_ckeditor,
    js_dependencies_jquery,
    js_dependencies_ui_sortable
)

js_main = NpmBundle(
    'node_modules/angular/angular.js',
    'node_modules/angular-sanitize/angular-sanitize.js',
    'node_modules/underscore/underscore.js',
    npm={
        'angular': '~1.5.8',
        'angular-sanitize': '~1.5.8',
        'underscore': '~1.8.3',
    }
)

js_dependecies_schema_form = NpmBundle(
    'node_modules/tv4/tv4.js',
    'node_modules/objectpath/lib/ObjectPath.js',
    'node_modules/angular-schema-form/dist/schema-form.js',
    'node_modules/angular-schema-form/dist/bootstrap-decorator.js',
    npm={
        'angular-schema-form': '~0.8.13',
        'angular-schema-form-bootstrap': '~0.2.0',
        'objectpath': '~1.2.1',
        'tv4': '~1.2.7',
    }
)

js_jquery = NpmBundle(
    js_dependencies_jquery,
    filters='jsmin',
    output='gen/cds.deposit.jquery.deposit.%(version)s.js',
)

js_cds_deposit = Bundle(
    # 'js/cds_deposit/cdsDeposit.module.js',
    'js/cds_deposit/avc/avc.module.js',
    'js/cds_deposit/avc/components/cdsActions.js',
    'js/cds_deposit/avc/components/cdsDeposit.js',
    'js/cds_deposit/avc/components/cdsDeposits.js',
    'js/cds_deposit/avc/components/cdsForm.js',
    'js/cds_deposit/avc/components/cdsUploader.js',
)

js_deposit = NpmBundle(
    js_main,
    js_dependecies_schema_form,
    js_dependecies_autocomplete,
    js_dependencies_ui_sortable,
    js_dependencies_ckeditor,
    js_dependecies_uploader,
    js_cds_deposit,
    filters='jsmin',
    output='gen/cds.deposit.%(version)s.js',
)
