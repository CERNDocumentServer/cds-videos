# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016, 2018 CERN.
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

import uuid

import pytest
from cds.modules.records.permissions import (has_admin_permission,
                                             record_permission_factory)
from flask_principal import RoleNeed, identity_loaded
from flask_security import login_user
from invenio_accounts.models import User
from invenio_records.api import Record


@pytest.mark.parametrize('access,action,is_allowed', [
    ({'foo': 'bar'}, 'read', True),
    ({'_access': {'read': [1, 'no-access@cern.ch',
                  'no-access-either@cern.ch']}}, 'read', True),
    ({'_access': {'read': [2, 'no-access@cern.ch']}}, 'read', False),
    ({'_access': {'read': ['test-egroup@cern.ch']}}, 'read', True),
    ({'_access': {'read': []}}, 'read', True),
    ({'foo': 'bar'}, 'create', True),
    ({'_access': {'create': [1, 'no-access@cern.ch',
                  'no-access-either@cern.ch']}}, 'create', True),
    ({'_access': {'create': [2, 'no-access@cern.ch']}}, 'create', True),
    ({'_access': {'create': ['test-egroup@cern.ch']}}, 'create', True),
    ({'_access': {'create': []}}, 'create', True),
    ({'foo': 'bar'}, 'read', True),
    ({'_access': {'read': [1, 'no-access@cern.ch',
                  'no-access-either@cern.ch']}}, 'read', True),
    ({'_access': {'read': [2, 'no-access@cern.ch']}}, 'read',
        False),
    ({'_access': {'read': ['test-egroup@cern.ch']}}, 'read', True),
    ({'_access': {'read': []}}, 'read', True),
    ({'foo': 'bar'}, 'update', False),
    ({'_access': {'update': [1, 'no-access@cern.ch',
                  'no-access-either@cern.ch']}}, 'update', True),
    ({'_access': {'update': [2, 'no-access@cern.ch']}}, 'update', False),
    ({'_access': {'update': ['test-egroup@cern.ch']}}, 'update', True),
    ({'_access': {'update': []}}, 'update', False),
    # Only admin can delete records
    ({'foo': 'bar'}, 'delete', False),
    ({'foo': 'bar'}, 'read-eos-path', False),
    ({'eos': 'true'}, 'read-eos-path', True),
])
def test_record_access(db, users, access, action, is_allowed):
    """Test access control for records."""
    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        roles = [RoleNeed('Test-Egroup@cern.ch')]
        if 'eos' in access:
            roles.append(RoleNeed('vmo-restictedrights@cern.ch'))
        identity.provides |= set(roles)

    def login_and_test(user_id):
        login_user(User.query.get(user_id))

        # Create record
        id = uuid.uuid4()
        record = Record.create(access, id_=id)

        # Check permission factory
        factory = record_permission_factory(record, action)
        if has_admin_permission():
            # super user can do EVERYTHING
            assert factory.can()
        else:
            assert factory.can() if is_allowed else not factory.can()

    # Test standard user
    login_and_test(1)
    # Now test that super-user can do all actions
    login_and_test(3)
