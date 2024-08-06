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

"""Deposit UI."""


from copy import deepcopy

from flask import Blueprint, current_app, render_template, request
from flask_login import login_required
from invenio_pidstore.errors import PIDDeletedError
from invenio_records_ui.signals import record_viewed

from ..proxies import current_deposit


def create_blueprint(endpoints):
    """Create Invenio-Deposit-UI blueprint.

    See: :data:`invenio_deposit.config.DEPOSIT_RECORDS_UI_ENDPOINTS`.

    :param endpoints: List of endpoints configuration.
    :returns: The configured blueprint.
    """
    from invenio_records_ui.views import create_url_rule

    blueprint = Blueprint(
        "invenio_deposit_ui",
        __name__,
        static_folder="../static",
        template_folder="../templates",
        url_prefix="",
    )

    @blueprint.errorhandler(PIDDeletedError)
    def tombstone_errorhandler(error):
        """Render tombstone page."""
        return (
            render_template(
                current_app.config["DEPOSIT_UI_TOMBSTONE_TEMPLATE"],
                pid=error.pid,
                record=error.record or {},
            ),
            410,
        )

    for endpoint, options in (endpoints or {}).items():
        options = deepcopy(options)
        options.pop("jsonschema", None)
        options.pop("schemaform", None)
        blueprint.add_url_rule(**create_url_rule(endpoint, **options))

    @blueprint.route("/deposit")
    @login_required
    def index():
        """List user deposits."""
        return render_template(current_app.config["DEPOSIT_UI_INDEX_TEMPLATE"])

    @blueprint.route("/deposit/new")
    @login_required
    def new():
        """Create new deposit."""
        deposit_type = request.values.get("type")
        return render_template(
            current_app.config["DEPOSIT_UI_NEW_TEMPLATE"],
            record={"_d`eposit": {"id": None}},
            jsonschema=current_deposit.jsonschemas[deposit_type],
            schemaform=current_deposit.schemaforms[deposit_type],
        )

    return blueprint


def default_view_method(pid, record, template=None):
    """Default view method.

    Sends ``record_viewed`` signal and renders template.
    """
    record_viewed.send(
        current_app._get_current_object(),
        pid=pid,
        record=record,
    )

    deposit_type = request.values.get("type")

    return render_template(
        template,
        pid=pid,
        record=record,
        jsonschema=current_deposit.jsonschemas[deposit_type],
        schemaform=current_deposit.schemaforms[deposit_type],
    )
