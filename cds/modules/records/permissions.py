# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Access control for CDS."""

from __future__ import absolute_import, print_function

from flask import g
from flask_principal import ActionNeed
from flask_security import current_user
from invenio_access import DynamicPermission


def record_permission_factory(record=None, action=None):
    """Record permission factory."""
    return RecordPermission.create(record, action)


def record_create_permission_factory(record=None):
    """Create permission factory."""
    return record_permission_factory(record=record, action='create')


def record_read_permission_factory(record=None):
    """Read permission factory."""
    return record_permission_factory(record=record, action='read')


def record_read_files_permission_factory(record=None):
    """Read permission factory."""
    return record_permission_factory(record=record, action='read-files')


def record_update_permission_factory(record=None):
    """Update permission factory."""
    return record_permission_factory(record=record, action='update')


def record_delete_permission_factory(record=None):
    """Delete permission factory."""
    return record_permission_factory(record=record, action='delete')


def deposit_read_permission_factory(record=None):
    """Record permission factory."""
    if record and 'deposits' in record['$schema']:
        return DepositPermission.create(record=record, action='read')
    else:
        return RecordPermission.create(record=record, action='read')


def deposit_delete_permission_factory(record=None):
    """Record permission factory."""
    return DepositPermission.create(record=record, action='delete')


#
# Permission classes
#
class RecordPermission(object):
    """Record permission.

    - Create action given to any authenticated user.
    - Read access given to everyone.
    - Update access given to record owners.
    - Delete access given to admins only.
    """

    create_actions = ['create']
    read_actions = ['read']
    read_files_actions = ['read-files']
    update_actions = ['update']
    delete_actions = ['delete']

    def __init__(self, record, func, user):
        """Initialize a file permission object."""
        self.record = record
        self.func = func
        self.user = user or current_user

    def can(self):
        """Determine access."""
        return self.func(self.user, self.record)

    @classmethod
    def create(cls, record, action, user=None):
        """Create a record permission."""
        if action in cls.create_actions:
            return cls(record, allow, user)
        elif action in cls.read_actions:
            return cls(record, allow, user)
        elif action in cls.read_files_actions:
            return cls(record, has_read_files_permission, user)
        elif action in cls.update_actions:
            return cls(record, has_update_permission, user)
        elif action in cls.delete_actions:
            return cls(record, has_admin_permission, user)
        else:
            return cls(record, deny, user)


class DepositPermission(RecordPermission):
    """Deposit permission.

    - Read action given to record owners.
    - Delete action given to record owners (still subject to being unpublished)
    """

    @classmethod
    def create(cls, record, action, user=None):
        """Create a deposit permission."""
        if action in cls.read_actions:
            return cls(record, has_update_permission, user)
        elif action in cls.delete_actions:
            return cls(record, has_update_permission, user)
        return super(DepositPermission, cls).create(record, action, user=user)


#
# Utility functions
#
def _get_user_provides():
    """Extract the user's provides from g."""
    return [str(need.value) for need in g.identity.provides]


def deny(user, record):
    """Deny access."""
    return False


def allow(user, record):
    """Allow access."""
    return True


def has_read_files_permission(user, record):
    """Check if user has read access to the record."""
    # Allow everyone for now
    # TODO: decide on files access rights
    return True


def has_update_permission(user, record):
    """Check if user has update access to the record."""
    # Allow owners
    user_id = int(user.get_id()) if user.is_authenticated else None
    if user_id in record.get('owners', []):
        return True
    deposit_owners = record.get('_deposit', {}).get('owners', [])
    if user_id in deposit_owners:
        return True
    # Allow e-group members
    user_groups = _get_user_provides()
    if set(user_groups).intersection(set(deposit_owners)):
        return True

    return has_admin_permission()


def has_admin_permission():
    """Check if user has admin access to record."""
    # Allow administrators
    if DynamicPermission(ActionNeed('admin-access')):
        return True
