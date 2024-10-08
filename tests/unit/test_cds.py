# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
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

"""Test cds package."""

import pytest
from flask import url_for


def test_version(app):
    """Test version import."""
    from cds import __version__

    assert __version__


def test_home(app):
    """Test homepage."""
    with app.test_client() as client:
        res = client.get(url_for("cds_home.index"))

        assert res.status_code == 200


def test_ping(app):
    """Test homepage."""
    with app.test_client() as client:
        res = client.get(url_for("cds_home.ping"))

        assert res.status_code == 200
