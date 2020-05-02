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

import uuid

from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import FilterEqual

from .models import Flow, Task


class FilterUUID(FilterEqual):
    """UUID aware filter."""

    def apply(self, query, value, alias):
        """Convert UUID."""
        return query.filter(self.column == uuid.UUID(value))


class FlowModelView(ModelView):
    """Flow Model view."""

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    column_display_all_relations = True

    column_list = ('id', 'name', 'payload', 'previous_id', 'created')

    column_filters = ('created', 'updated')
    column_default_sort = ('updated', True)
    page_size = 25


class TaskModelView(ModelView):
    """Flow Model view."""

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    column_display_all_relations = True

    column_list = ('id', 'name', 'flow_id', 'status', 'message', 'payload')

    column_filters = ('name', FilterUUID(Task.flow_id, 'Flow'))
    column_default_sort = ('flow_id', True)
    page_size = 25


flow_model_view = dict(
    modelview=FlowModelView, model=Flow, name='Flows', category='Flows',
)

task_model_view = dict(
    modelview=TaskModelView, model=Task, name='Tasks', category='Flows',
)
