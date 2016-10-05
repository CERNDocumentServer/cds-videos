# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015 CERN.
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

"""Test access control package."""

from __future__ import absolute_import, print_function

import mock
import pytest
from cds.modules.records.minters import recid_minter
from invenio_pidstore.models import PIDStatus


def test_recid_provider(db):
    """Test the CDS recid provider."""
    with mock.patch('requests.get') as httpmock, mock.patch(
            'invenio_pidstore.models.PersistentIdentifier.create')\
            as pid_create:
        pid_create.configure_mock(**{'return_value.pid_provider': None,
                                     'return_value.pid_value': 1})
        httpmock.return_value.text = '1'

        data = dict()
        uuid = '12345678123456781234567812345678'
        recid_minter(uuid, data)

        assert data['recid'] == 1
        pid_create.assert_called_once_with(
            'recid', '1', pid_provider=None, object_type='rec',
            object_uuid=uuid, status=PIDStatus.REGISTERED)


def test_recid_provider_exception(db):
    """Test if providing a recid will cause an error."""
    with pytest.raises(AssertionError):
        recid_minter('12345678123456781234567812345678', dict({'recid': 1}))
