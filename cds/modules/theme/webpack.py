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
                "cds_theme_app": "./js/cds/app.js",
                "cds_theme_styles": "./less/cds/cds.less",
                "cds_deposit_app": "./js/cds_deposit/app.js",
                "cds_previewer_styles": "./less/cds_previewer/video.less",
                "cds_records_app": "./js/cds_records/app.js",
                "cds_records_stats_app": "./js/cds_records/stats.js",
                # The styles of invenio-charts-js are SCSS, built by sass-loader
                "cds_records_stats_styles": [
                    "invenio-charts-js/src/styles/styles.scss",
                    "./less/cds_records/stats.less",
                ],
                "cds_search_ui_app": "./js/cds_search_ui/app.js",
            },
            dependencies={
                "react": "^16.13.0",
                "react-dom": "^16.13.0",
                "prop-types": "^15.7.2",
                "semantic-ui-react": "^2.1.0",
                "semantic-ui-less": "^2.4.1",
                # react-searchkit 3.0.0 is the last release compatible with
                # react-overridable 0.0.3 (pinned by Invenio-Search-UI 3.0.x).
                # ``<3.0.1`` resolves to 3.0.0 and wins the version merge
                # against the ``^3.0.0`` of Invenio-Search-UI.
                "react-searchkit": "<3.0.1",
                "formik": "^2.4.0",
                # The deposit form state, same ranges as react-searchkit
                "redux": "^4.0.0",
                "react-redux": "^7.2.0",
                "redux-thunk": "^2.3.0",
                "axios": "^1.7.7",
                "lodash": "^4.17.4",
                "qs": "^6.8.0",
                "d3": "^3.5.17",
                "vtt.js": "~0.13.0",
                "dompurify": "^2.4.5",
                "ckeditor": "4.12.1",
                "invenio-charts-js": "^0.2.7",
                # Not used by CDS, but required by Invenio-Search-UI with
                # ``^4.0.0``: the latest 4.x releases need react-overridable
                # 1.x while Invenio-Search-UI pins react-overridable 0.0.3, so
                # keep the last release line compatible with both.
                "react-invenio-forms": "~4.10.0",
            },
            aliases={
                "@js/cds": "js/cds",
                "@js/cds_deposit": "js/cds_deposit",
                "@js/cds_records": "js/cds_records",
                "@js/cds_search_ui": "js/cds_search_ui",
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
