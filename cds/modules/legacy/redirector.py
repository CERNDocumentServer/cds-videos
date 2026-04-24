# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2025 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Redirector functions and rules."""

from flask import Blueprint, abort, current_app, redirect
from invenio_pidstore.errors import PIDDoesNotExistError, ResolverError
from sqlalchemy.orm.exc import NoResultFound

from cds.modules.records.resolver import record_resolver
from cds.modules.records.utils import is_project_record

from .resolver import get_pid_by_legacy_recid

HTTP_MOVED_PERMANENTLY = 301

blueprint = Blueprint(
    "cds_legacy", __name__, template_folder="templates", url_prefix="/legacy"
)


@blueprint.route("/record/<legacy_id>", strict_slashes=False)
def legacy_record_redirect(legacy_id):
    """Redirect legacy recid."""
    try:
        pid = get_pid_by_legacy_recid(legacy_id)
    except NoResultFound:
        abort(404)

    url_path = f"{current_app.config['SITE_URL']}/record/{pid.pid_value}"
    return redirect(url_path, HTTP_MOVED_PERMANENTLY)


@blueprint.route("/record/<legacy_id>/embed", strict_slashes=False)
def legacy_record_embed_redirect(legacy_id):
    """Redirect legacy recid to record embed view."""
    try:
        pid = get_pid_by_legacy_recid(legacy_id)
    except NoResultFound:
        abort(404)

    url_path = f"{current_app.config['SITE_URL']}/record/{pid.pid_value}/embed"
    return redirect(url_path, HTTP_MOVED_PERMANENTLY)


@blueprint.route("/record/<legacy_id>/files/<file_name>", strict_slashes=False)
def legacy_record_file_redirect(legacy_id, file_name):
    """Redirect legacy recid file to new file download link."""

    def _find_file_url(record):
        for file_ in record.get("_files", []):
            if file_.get("key") == file_name:
                return (file_.get("links", {}).get("self"))
        return None

    try:
        pid = get_pid_by_legacy_recid(legacy_id)
        _, record = record_resolver.resolve(pid_value=pid.pid_value)
    except (NoResultFound, PIDDoesNotExistError, ResolverError, KeyError, TypeError):
        abort(404)

    # Video record, try to get the file from the record
    if not is_project_record(record):
        url = _find_file_url(record)
        if url:
            return redirect(url, HTTP_MOVED_PERMANENTLY)
        abort(404)

    # Project record, try to get the file from the video records
    for video in record.get("videos", []):
        try:
            video_pid = video["$ref"].rstrip("/").split("/")[-1]
            _, video_record = record_resolver.resolve(pid_value=video_pid)
        except (PIDDoesNotExistError, ResolverError, KeyError, TypeError):
            continue

        url = _find_file_url(video_record)
        if url:
            return redirect(url, HTTP_MOVED_PERMANENTLY)

    abort(404)
