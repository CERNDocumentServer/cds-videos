# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""CDS interface."""


from flask import Blueprint, current_app, render_template
from invenio_pages.records.errors import PageNotFoundError
from invenio_pages.views import create_page_view

blueprint = Blueprint(
    "cds", __name__, template_folder="templates", static_folder="static"
)

#: Static pages (Invenio-Pages), created by ``cds fixtures pages``
PAGES = ("/about", "/contact", "/faq", "/guide/search", "/terms")

for url in PAGES:
    blueprint.add_url_rule(
        url,
        endpoint="page_" + url.strip("/").replace("/", "_"),
        view_func=create_page_view(url),
    )


@blueprint.app_errorhandler(PageNotFoundError)
def page_not_found(error):
    """Not found page for the static pages missing from the database."""
    return render_template(current_app.config["THEME_404_TEMPLATE"]), 404
