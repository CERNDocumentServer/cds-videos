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


from functools import partial
from urllib.parse import urljoin

from flask import current_app, request, url_for
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from invenio_records_rest.links import default_links_factory

from cds.modules.deposit.api import is_project_record
from cds.modules.records.permissions import deposit_update_permission_factory
from cds.modules.records.resolver import record_resolver

# The deposit of a project as plain metadata. ``project_resolver`` builds a
# ``Project``, which loads the task status and the files of all its videos,
# while the links only need the identifier and the access of the deposit.
deposit_metadata_resolver = Resolver(
    pid_type="depid",
    object_type="rec",
    getter=partial(Record.get_record, with_deleted=True),
)


def _api_record_url(pid_value):
    """URL of a record in the REST API."""
    return url_for(
        "invenio_records_rest.recid_item", pid_value=pid_value, _external=True
    )


def _build_record_project_links(project_pid, api_url=_api_record_url):
    """Get project links."""
    return {
        "project": api_url(project_pid.pid_value),
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


def _fill_video_extra_links(record, links, api_url=_api_record_url):
    """Add extra links if it's a video."""
    project = None
    try:
        pid, project = record_resolver.resolve(record["_project_id"])
        # include record project links
        links.update(**_build_record_project_links(project_pid=pid, api_url=api_url))
    except KeyError:
        # Most likely are dealing with a project
        if is_project_record(record):
            project = record
    except PIDDoesNotExistError:
        # The project has not being published yet
        try:
            pid, project = deposit_metadata_resolver.resolve(record["_project_id"])
        except PIDDoesNotExistError:
            pass

    try:
        # include deposit project links
        if project:
            links.update(
                **_build_deposit_project_links(
                    deposit_project=deposit_metadata_resolver.resolve(
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


def record_ui_link_factory(pid, record):
    """The links of ``record_link_factory``, for the pages of the UI app.

    The REST endpoints only exist in the API application, so their URLs are
    built from the request (``/api/record/<pid_value>``).
    """

    def api_url(pid_value):
        return urljoin(request.host_url, "api/record/{0}".format(pid_value))

    try:
        links = {"self": api_url(pid.pid_value)}
        _fill_video_extra_links(record=record, links=links, api_url=api_url)
        return links
    except Exception:
        return {}
