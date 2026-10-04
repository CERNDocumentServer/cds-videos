# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Initialization of XRootD."""


from importlib import metadata

try:
    # Check if xrootdpyfs is installed
    metadata.version("xrootdpyfs")
    import xrootdpyfs  # noqa

    XROOTD_ENABLED = True
except metadata.PackageNotFoundError:
    XROOTD_ENABLED = False
    xrootdpyfs = None


class CDSXRootD(object):
    """CDS xrootd extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.config["XROOTD_ENABLED"] = XROOTD_ENABLED
        if XROOTD_ENABLED:
            #: Overwrite reported checksum from CERN EOS (due to XRootD 3.3.6).
            app.config["XROOTD_CHECKSUM_ALGO"] = "md5"
            app.config["FILES_REST_STORAGE_FACTORY"] = (
                "invenio_xrootd:eos_storage_factory"
            )
        app.extensions["cds-xrootd"] = self
