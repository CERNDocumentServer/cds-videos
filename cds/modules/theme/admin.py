# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2026 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Admin view of the static pages.

Invenio-Pages moved its page editor to Invenio-Administration. CDS keeps
the pages in the Invenio-Admin panel, as before.
"""

from flask import current_app
from flask_admin.contrib.sqla import ModelView
from invenio_pages import PageModel
from markupsafe import Markup
from wtforms import SelectField, TextAreaField


class PagesModelView(ModelView):
    """Static pages admin view."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 100

    column_list = ("url", "lang", "title", "template_name", "updated", "link")
    column_details_list = (
        "url",
        "lang",
        "title",
        "template_name",
        "description",
        "content",
        "created",
        "updated",
    )
    column_searchable_list = ("url", "title", "content", "description")
    column_filters = ("url", "lang", "title", "template_name")
    column_labels = dict(url="URL", lang="Language")
    column_default_sort = "url"
    column_formatters = dict(
        link=lambda v, c, m, p: Markup('<a href="{0}">View</a>').format(m.url),
        content=lambda v, c, m, p: Markup(m.content),
    )

    form_columns = ("url", "lang", "title", "description", "content", "template_name")
    form_overrides = dict(
        content=TextAreaField,
        description=TextAreaField,
        template_name=SelectField,
    )
    form_args = dict(
        template_name=dict(choices=lambda: current_app.config["PAGES_TEMPLATES"]),
    )
    form_widget_args = dict(content=dict(rows=25))


pages_adminview = dict(
    modelview=PagesModelView,
    model=PageModel,
    name="Pages",
    category="Pages",
    # Same URL as the former Invenio-Pages admin view (/admin/page/)
    endpoint="page",
)
