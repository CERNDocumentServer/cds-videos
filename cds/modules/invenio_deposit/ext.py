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

"""Module for depositing record metadata and uploading files."""

from __future__ import absolute_import, print_function

from collections import defaultdict

from invenio_records_rest import utils
from werkzeug.utils import cached_property

from . import config
from .views import rest, ui


class _DepositState(object):
    """Deposit state."""

    def __init__(self, app):
        """Initialize state."""
        self.app = app

    @cached_property
    def jsonschemas(self):
        """Load deposit JSON schemas."""
        _jsonschemas = {
            k: v["jsonschema"]
            for k, v in self.app.config["DEPOSIT_RECORDS_UI_ENDPOINTS"].items()
            if "jsonschema" in v
        }
        return defaultdict(
            lambda: self.app.config["DEPOSIT_DEFAULT_JSONSCHEMA"], _jsonschemas
        )

    @cached_property
    def schemaforms(self):
        """Load deposit schema forms."""
        _schemaforms = {
            k: v["schemaform"]
            for k, v in self.app.config["DEPOSIT_RECORDS_UI_ENDPOINTS"].items()
            if "schemaform" in v
        }
        return defaultdict(
            lambda: self.app.config["DEPOSIT_DEFAULT_SCHEMAFORM"], _schemaforms
        )


class InvenioDeposit(object):
    """Invenio-Deposit extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization.

        Initialize the UI endpoints.

        :param app: An instance of :class:`flask.Flask`.
        """
        self.init_config(app)
        app.register_blueprint(
            ui.create_blueprint(app.config["DEPOSIT_RECORDS_UI_ENDPOINTS"])
        )
        app.extensions["invenio-deposit"] = _DepositState(app)

    def init_config(self, app):
        """Initialize configuration.

        :param app: An instance of :class:`flask.Flask`.
        """
        for k in dir(config):
            if k.startswith("DEPOSIT_"):
                app.config.setdefault(k, getattr(config, k))


class InvenioDepositREST(object):
    """Invenio-Deposit REST extension."""

    def __init__(self, app=None):
        """Extension initialization.

        :param app: An instance of :class:`flask.Flask`.
        """
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization.

        Initialize the REST endpoints.

        :param app: An instance of :class:`flask.Flask`.
        """
        self.init_config(app)
        blueprint = rest.create_blueprint(app.config["DEPOSIT_REST_ENDPOINTS"])

        # FIXME: This is a temporary fix. This means that
        # invenio-records-rest's endpoint_prefixes cannot be used before
        # the first request or in other processes, ex: Celery tasks.
        @app.before_first_request
        def extend_default_endpoint_prefixes():
            """Extend redirects between PID types."""
            endpoint_prefixes = utils.build_default_endpoint_prefixes(
                dict(app.config["DEPOSIT_REST_ENDPOINTS"])
            )
            current_records_rest = app.extensions["invenio-records-rest"]
            overlap = set(endpoint_prefixes.keys()) & set(
                current_records_rest.default_endpoint_prefixes
            )
            if overlap:
                raise RuntimeError(
                    "Deposit wants to override endpoint prefixes {0}.".format(
                        ", ".join(overlap)
                    )
                )
            current_records_rest.default_endpoint_prefixes.update(endpoint_prefixes)

        app.register_blueprint(blueprint)
        app.extensions["invenio-deposit-rest"] = _DepositState(app)

    def init_config(self, app):
        """Initialize configuration.

        :param app: An instance of :class:`flask.Flask`.
        """
        for k in dir(config):
            if k.startswith("DEPOSIT_"):
                app.config.setdefault(k, getattr(config, k))
