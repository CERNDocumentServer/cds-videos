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

from cds.modules.deposit.api import is_project_record, project_resolver
from cds.modules.records.permissions import deposit_update_permission_factory
from cds.modules.records.resolver import record_resolver
from flask import current_app, request, url_for
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_records_rest.links import default_links_factory


def _build_record_project_links(project_pid):
    """Get project links."""
    return {
        "project": url_for(
            "invenio_records_rest.recid_item",
            pid_value=project_pid.pid_value,
            _external=True,
        ),
        "project_html": current_app.config["RECORD_UI_ENDPOINT"].format(
            scheme=request.scheme,
            host=request.host,
            pid_value=project_pid.pid_value,
        ),
    }


def _build_deposit_project_links(deposit_project):
    """Get deposit video links."""
    project_pid, deposit = deposit_project
    url = current_app.config["DEPOSIT_PROJECT_UI_ENDPOINT"]
    links = {}
    if deposit_update_permission_factory(record=deposit).can():
        links["project_edit"] = url.format(
            scheme=request.scheme,
            host=request.host,
            pid_value=project_pid.pid_value,
        )
    return links


def _fill_video_extra_links(record, links):
    """Add extra links if it's a video."""
    project = None
    try:
        pid, project = record_resolver.resolve(record["_project_id"])
        # include record project links
        links.update(**_build_record_project_links(project_pid=pid))
    except KeyError:
        # Most likely are dealing with a project
        if is_project_record(record):
            project = record
    except PIDDoesNotExistError:
        # The project has not being published yet
        try:
            pid, project = project_resolver.resolve(record["_project_id"])
        except PIDDoesNotExistError:
            pass

    try:
        # include deposit project links
        if project:
            links.update(
                **_build_deposit_project_links(
                    deposit_project=project_resolver.resolve(
                        project["_deposit"]["id"]
                    )
                )
            )
    except (KeyError, PIDDoesNotExistError):
        pass


def record_link_factory(pid):
    """Record link creation."""
    try:
        links = default_links_factory(pid=pid)
        _, record = record_resolver.resolve(pid_value=pid.pid_value)
        _fill_video_extra_links(record=record, links=links)
        return links
    except Exception:
        return {}
