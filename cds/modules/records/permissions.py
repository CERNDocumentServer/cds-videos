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

from flask import current_app
from flask_security import current_user
from invenio_access import DynamicPermission
from invenio_files_rest.models import Bucket, MultipartObject, ObjectVersion
from invenio_records_files.api import FileObject
from invenio_records_files.models import RecordsBuckets
from invenio_deposit.permissions import action_admin_access

from .utils import is_deposit, is_record, get_user_provides
from .api import CDSRecord as Record


def files_permission_factory(obj, action=None):
    """Permission for files are always based on the type of bucket.

    1. Community bucket: Read access for everyone
    2. Record bucket: Read access only with open and restricted access.
    3. Deposit bucket: Read/update with restricted access.
    4. Any other bucket is restricted to admins only.
    """
    # Extract bucket id
    bucket_id = None
    if isinstance(obj, Bucket):
        bucket_id = str(obj.id)
    elif isinstance(obj, ObjectVersion):
        bucket_id = str(obj.bucket_id)
    elif isinstance(obj, MultipartObject):
        bucket_id = str(obj.bucket_id)
    elif isinstance(obj, FileObject):
        bucket_id = str(obj.bucket_id)

    # Retrieve record
    if bucket_id is not None:
        # Record or deposit bucket
        rb = RecordsBuckets.query.filter_by(bucket_id=bucket_id).one_or_none()
        if rb is not None:
            record = Record.get_record(rb.record_id)
            if is_record(record):
                return RecordFilesPermission.create(record, action)
            elif is_deposit(record):
                return DepositFilesPermission.create(record, action)

    return DynamicPermission(action_admin_access).can()


def record_permission_factory(record=None, action=None):
    """Record permission factory."""
    return RecordPermission.create(record, action)


def record_create_permission_factory(record=None):
    """Create permission factory."""
    return record_permission_factory(record=record, action='create')


def record_read_permission_factory(record=None):
    """Read permission factory."""
    return record_permission_factory(record=record, action='read')


def record_read_eos_path_permission_factory(record=None):
    """Read permission factory."""
    return record_permission_factory(record=record, action='read-eos-path')


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


def deposit_update_permission_factory(record=None):
    """Deposit permission factory."""
    return DepositPermission.create(record=record, action='update')


def deposit_delete_permission_factory(record=None):
    """Deposit permission factory."""
    return DepositPermission.create(record=record, action='delete')


#
# Permission classes
#
class DepositFilesPermission(object):
    """Permission for files in deposit records (read and update access).

    Read and update access given to owners and administrators.
    """

    update_actions = [
        'bucket-read',
        'bucket-read-versions',
        'bucket-update',
        'bucket-listmultiparts',
        'object-read',
        'object-read-version',
        'object-delete',
        'object-delete-version',
        'multipart-read',
        'multipart-delete',
    ]

    def __init__(self, record, func):
        """Initialize a file permission object."""
        self.record = record
        self.func = func

    def can(self):
        """Determine access."""
        return self.func(current_user, self.record)

    @classmethod
    def create(cls, record, action):
        """Record and instance."""
        if action in cls.update_actions:
            return cls(record, has_update_permission)
        else:
            return cls(record, has_admin_permission)


class RecordFilesPermission(DepositFilesPermission):
    """Permission for files in published records (read only access).

    Read access (list and download) granted to:

      1. Everyone if record is open access.
      2. Owners, token bearers and administrators if embargoed, restricted or
         closed access

    Read version access granted to:

      1. Administrators only.
    """

    read_actions = [
        'bucket-read',
        'object-read',
    ]

    admin_actions = [
        'bucket-read',
        'bucket-read-versions',
        'object-read',
        'object-read-version',
    ]

    @classmethod
    def create(cls, record, action):
        """Create a record files permission."""
        if action in cls.read_actions:
            return cls(record, has_read_files_permission)
        elif action in cls.admin_actions:
            return cls(record, has_admin_permission)
        else:
            return cls(record, deny)


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
    read_eos_path_actions = ['read-eos-path']
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
            return cls(record, has_read_record_permission, user)
        elif action in cls.read_eos_path_actions:
            return cls(record, has_read_record_eos_path_permission, user)
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
        if action in cls.update_actions:
            return cls(record, has_update_permission, user)
        elif action in cls.delete_actions:
            return cls(record, has_update_permission, user)
        return super(DepositPermission, cls).create(record, action, user=user)


#
# Utility functions
#
def deny(user, record):
    """Deny access."""
    return False


def allow(user, record):
    """Allow access."""
    return True


def is_public(data, action):
    """Check if the record is fully public.

    In practice this means that the record doesn't have the ``access`` key or
    the action is not inside access or is empty.
    """
    return '_access' not in data or not data.get('_access', {}).get(action)


def has_read_files_permission(user, record):
    """Check if user has read access to the record's files."""
    # TODO: decide on files access rights
    # Same permissions as for record itself

    # Allow everyone for public records
    if is_public(record, 'read'):
        return True

    # Allow e-group members
    user_provides = get_user_provides()
    read_access_groups = record['_access']['read']

    if not set(user_provides).isdisjoint(set(read_access_groups)):
        return True

    return has_admin_permission(user, record)


def has_read_record_permission(user, record):
    """Check if user has read access to the record."""
    # Allow everyone for public records
    if is_public(record, 'read'):
        return True

    # Allow e-group members
    user_provides = get_user_provides()
    read_access_groups = record['_access']['read']

    if not set(user_provides).isdisjoint(set(read_access_groups)):
        return True

    return has_admin_permission()


def has_read_record_eos_path_permission(user, record):
    """Check if user has eos path permissions."""
    user_provides = get_user_provides()
    # Allow e-group members only
    read_access_groups = current_app.config.get('VIDEOS_EOS_PATH_EGROUPS', [])

    if not set(user_provides).isdisjoint(set(read_access_groups)):
        return True
    return has_admin_permission(user, record)


def has_update_permission(user, record):
    """Check if user has update access to the record."""
    user_id = int(user.get_id()) if user.is_authenticated else None

    # Allow owners
    deposit_creator = record.get('_deposit', {}).get('created_by', -1)
    if user_id == deposit_creator:
        return True

    # Allow based in the '_access' key
    user_provides = get_user_provides()
    # set.isdisjoint() is faster than set.intersection()
    allowed_users = record.get('_access', {}).get('update', [])
    if allowed_users and not set(user_provides).isdisjoint(set(allowed_users)):
        return True

    return has_admin_permission()


def has_admin_permission(user=None, record=None):
    """Check if user has admin access to record.

    This function has to accept 2 parameters (as all other has_foo_permissions,
    to allow for dynamic dispatch.
    """
    # Allow administrators
    return DynamicPermission(action_admin_access).can()
