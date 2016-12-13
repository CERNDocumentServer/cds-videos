# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
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

"""Test cds minters."""

from __future__ import absolute_import, print_function

from uuid import uuid4

import mock
import pytest
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from cds.modules.records.minters import recid_minter


def test_double_minting_depid_recid(db):
    """Test using same integer for dep/rec ids."""
    data = dict()
    # Assert registration of recid.
    rec_uuid = uuid4()
    pid = recid_minter(rec_uuid, data)
    assert pid.pid_type == 'recid'
    assert pid.pid_value == '1'
    assert pid.status == PIDStatus.REGISTERED
    assert pid.object_uuid == rec_uuid
    assert data['doi'] == '10.0000/cds.1'
