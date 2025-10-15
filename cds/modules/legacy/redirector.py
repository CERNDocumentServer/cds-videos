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
from sqlalchemy.orm.exc import NoResultFound

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
