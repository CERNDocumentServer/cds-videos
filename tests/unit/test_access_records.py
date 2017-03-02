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

"""Test access control package."""

from __future__ import absolute_import, print_function

import uuid

from flask_principal import RoleNeed, identity_loaded
from flask_security import login_user
from invenio_accounts.models import User
from invenio_records.api import Record
from cds.modules.records.permissions import (has_admin_permission,
                                             record_permission_factory)


def test_record_access(db, users):
    """Test access control for records."""
    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed('test-egroup@cern.ch')])

    user_id = 1
    login_user(User.query.get(user_id))

    def check_record(json, action='read', allowed=True):
        # Create uuid
        id = uuid.uuid4()

        # Create record
        record = Record.create(json, id_=id)

        # Check permission factory
        factory = record_permission_factory(record, action)
        assert factory.can() if allowed else not factory.can()

    # Check test records
    check_record({'foo': 'bar'})
    check_record({
        '_access': {
            'read': [
                user_id,
                'no-access@cern.ch',
                'no-access-either@cern.ch'
            ]
        }
    })
    check_record({
        '_access': {
            'read': [
                user_id + 1,
                'no-access@cern.ch'
            ]
        }
    }, allowed=False)
    check_record({'_access': {'read': ['test-egroup@cern.ch']}})
    check_record({'_access': {'read': []}})


def test_not_all_users_are_admins(app, users):
    """Test that not all the users have admin access."""
    login_user(User.query.get(users[0]))
    assert not has_admin_permission()

    # users[2] is the admin
    login_user(User.query.get(users[2]))
    assert has_admin_permission()
