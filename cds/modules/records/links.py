# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

from flask import url_for, current_app, request
from invenio_records_rest.links import default_links_factory

from .resolver import record_resolver, get_record_pid
from ..deposit.api import deposit_project_resolver


def _fill_video_extra_links(record, links):
    """Add extra links if it's a video."""
    if '_project_id' in record:
        # if it's a video, get the deposit project
        deposit_project = deposit_project_resolver(record['_project_id'])
        if deposit_project.is_published():
            # if the project is published, get the record project
            pid_project = get_record_pid(
                pid_value=deposit_project['_deposit']['pid']['value'])
            # include project link
            api_url = url_for('invenio_records_rest.recid_item',
                              pid_value=pid_project.pid_value, _external=True)
            url = current_app.config['RECORD_UI_ENDPOINT'].format(
                scheme=request.scheme,
                host=request.host,
                pid_value=pid_project.pid_value,
            )
            links.update(project=api_url, project_html=url)


def record_link_factory(pid):
    """Record link creation."""
    links = default_links_factory(pid=pid)
    _, record = record_resolver.resolve(pid_value=pid.pid_value)
    _fill_video_extra_links(record=record, links=links)

    return links
