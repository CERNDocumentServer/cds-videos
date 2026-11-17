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

"""JS/CSS bundles for search-ui.

You include one of the bundles in a page like the example below (using
``base`` bundle as an example):

 .. code-block:: html

    {{ webpack['base.js']}}

"""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    "assets",
    default="semantic-ui",
    themes={
        "semantic-ui": dict(
            entry={
                "cds_theme_app": "./js/cds/entries/theme.js",
                "cds_theme_styles": "./less/cds/cds.less",
                "cds_deposit_app": "./js/cds/entries/deposit.js",
                "cds_previewer_styles": "./less/cds_previewer/video.less",
                "cds_records_app": "./js/cds/entries/record.js",
                "cds_records_stats_app": "./js/cds/entries/recordStats.js",
                # The styles of invenio-charts-js are SCSS, built by sass-loader
                "cds_records_stats_styles": [
                    "invenio-charts-js/src/styles/styles.scss",
                    "./less/cds_records/stats.less",
                ],
                "cds_search_ui_app": "./js/cds/entries/search.js",
                # The Invenio-Admin panel, Font Awesome 4 is a dependency of
                # its bundle in Invenio-Theme
                "cds_admin_styles": [
                    "font-awesome/css/font-awesome.css",
                    "./less/cds_admin/admin.less",
                ],
            },
            dependencies={
                # Same majors as Invenio-Search-UI
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "prop-types": "^15.7.2",
                "semantic-ui-react": "^3.0.0-beta.2",
                "semantic-ui-less": "^2.4.1",
                "react-searchkit": "^4.0.0",
                "formik": "^2.4.0",
                # The deposit form state, same ranges as react-searchkit
                "redux": "^4.0.0",
                "react-redux": "^7.2.0",
                "redux-thunk": "^2.3.0",
                "axios": "^1.7.7",
                "lodash": "^4.17.4",
                # Same range as semantic-ui-react, so one copy
                "clsx": "^1.1.1",
                "qs": "^6.8.0",
                "d3": "^3.5.17",
                "vtt.js": "~0.13.0",
                "dompurify": "^2.4.5",
                # The editor of the descriptions, same ranges as
                # Invenio-Administration (which copies its skins)
                "hugerte": "^1.0.10",
                "@hugerte/hugerte-react": "^2.0.2",
                "invenio-charts-js": "^0.2.7",
            },
            aliases={
                "@js/cds": "js/cds",
                "@less/cds": "less/cds",
                # react-searchkit points bundlers to its CommonJS build (its
                # ``browser`` field), which pulls a second copy of axios and
                # can not be tree shaken: use its ES modules build.
                "react-searchkit$": "node_modules/react-searchkit/dist/esm/index.js",
                # Semantic-UI theme configuration used by Invenio-Theme to
                # build Semantic UI (``theme.js`` entry point).
                "../../theme.config$": "less/theme.config",
                "../../less/site": "less/site",
                "../../less": "less",
            },
        ),
    },
)
