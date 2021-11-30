# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2020 CERN.
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

"""Admin model views for Flows."""

from flask import url_for
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from invenio_admin.filters import FilterConverter
from markupsafe import Markup

from .models import FlowMetadata, FlowTaskMetadata


def link(text, link_func):
    """Generate a object formatter for links.."""

    def object_formatter(v, c, m, p):
        """Format object view link."""
        return Markup('<a href="{0}">{1}</a>'.format(link_func(m), text))

    return object_formatter


class FlowModelView(ModelView):
    """Flow Model view."""

    filter_converter = FilterConverter()
    can_create = False
    can_edit = True
    can_delete = False
    can_view_details = True
    column_formatters = dict(
        tasks=link(
            "Tasks", lambda o: url_for("taskmetadata.index_view", search=o.id)
        )
    )

    column_list = (
        "id",
        "name",
        "deposit_id",
        "payload",
        "user_id",
        "is_last",
        "created",
        "tasks",
    )
    column_labels = {
        "id": "UUID",
    }

    column_searchable_list = ("id", "deposit_id", "payload")
    column_default_sort = ("updated", True)
    page_size = 25


class TaskModelView(ModelView):
    """Flow Model view."""

    filter_converter = FilterConverter()
    can_create = False
    can_edit = True
    can_delete = False
    can_view_details = True
    form_base_class = FlaskForm

    column_list = ("id", "name", "flow.id", "status", "payload", "message")
    column_labels = {
        "id": "UUID",
        "flow.id": "Flow UUID",
    }
    column_searchable_list = ("flow.id", "name", "status")
    column_default_sort = ("flow_id", True)
    page_size = 25


flow_model_view = dict(
    modelview=FlowModelView,
    model=FlowMetadata,
    name="Flows",
    category="Flows",
)

task_model_view = dict(
    modelview=TaskModelView,
    model=FlowTaskMetadata,
    name="Tasks",
    category="Flows",
)
