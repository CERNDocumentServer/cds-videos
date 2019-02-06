# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2019 CERN.
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

"""Links for record serialization."""

from __future__ import absolute_import, print_function

from flask import current_app, request, url_for
from invenio_deposit.utils import extract_actions_from_class
from invenio_records_files.links import default_bucket_link_factory

from ..records.permissions import has_custom_deposit_action_permission
from ..records.resolver import get_pid
from .api import Project, Video


def deposit_links_factory(pid, deposit_type=None):
    """Factory for links generation."""
    type_exists = deposit_type is not None
    deposit_type = deposit_type or pid.pid_type

    def _url(name, **kwargs):
        """URL builder."""
        endpoint = '.{0}_{1}'.format(deposit_type, name)
        return url_for(endpoint, pid_value=pid.pid_value, _external=True,
                       **kwargs)
    links = {}
    bucket_link = default_bucket_link_factory(pid)
    if bucket_link is not None:
        links['bucket'] = bucket_link
    links['self'] = _url('item')
    links['files'] = _url('files')
    ui_endpoint = current_app.config.get(
        'DEPOSIT_UI_ENDPOINT' if type_exists else 'DEPOSIT_UI_ENDPOINT_DEFAULT'
    )
    if ui_endpoint is not None:
        links['html'] = ui_endpoint.format(
            host=request.host,
            scheme=request.scheme,
            type=deposit_type,
            pid_value=pid.pid_value,
        )
    deposit_cls = Video if deposit_type == 'video' else Project
    deposit  = deposit_cls.get_record(
        get_pid('depid', pid.pid_value).object_uuid)
    for action in extract_actions_from_class(deposit_cls):
        if action not in ('publish', 'edit', 'discard') and \
                not has_custom_deposit_action_permission(
                    action, record=deposit):
            #The user can't perform this action
            continue
        links[action] = _url('actions', action=action)
    return links


def project_links_factory(pid):
    """Project factory for links generation."""
    # cannot use partial func because of invenio-records-rest#183
    return deposit_links_factory(pid, deposit_type='project')


def video_links_factory(pid):
    """Video factory for links generation."""
    # cannot use partial func because of invenio-records-rest#183
    return deposit_links_factory(pid, deposit_type='video')
