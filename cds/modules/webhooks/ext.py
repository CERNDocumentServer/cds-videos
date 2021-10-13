# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Fixtures."""

from __future__ import absolute_import, print_function
import pkg_resources


class CDSFlows(object):
    """CDS fixtures extension."""

    def __init__(self, app=None, entry_point_group="cds_flows.receivers"):
        """Extension initialization."""
        self.receivers = {}

        if entry_point_group:
            self.load_entry_point_group(entry_point_group)
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.extensions['cds-flows'] = self

    def load_entry_point_group(self, entry_point_group):
        """Load actions from an entry point group."""
        for ep in pkg_resources.iter_entry_points(group=entry_point_group):
            self.register(ep.name, ep.load())

    def register(self, receiver_id, receiver):
        """Register a receiver."""
        assert receiver_id not in self.receivers
        self.receivers[receiver_id] = receiver(receiver_id)
