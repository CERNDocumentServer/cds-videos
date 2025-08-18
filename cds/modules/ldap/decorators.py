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

"""CDS LDAP decorators."""

from functools import wraps

from flask_login import current_user
from flask import abort, current_app


def needs_authentication(func):
    """Decorator for API call to check if user is authenticated."""
    @wraps(func)
    def decorated_api_view(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return func(*args, **kwargs)
    return decorated_api_view


def cern_user_required():
    """Restrict access based on roles from RemoteAccount.extra_data["roles"]."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized (not logged in)

            allowed_roles = current_app.config.get("UPLOAD_ALLOWED_ROLES", [])

            # Collect roles from all RemoteAccounts
            remote_account_roles = []
            for ra in getattr(current_user, "remote_accounts", []):
                if not ra.extra_data:
                    continue
                roles = ra.extra_data.get("roles", [])
                if isinstance(roles, list):
                    remote_account_roles.extend(roles)

            # If user has at least one allowed role → grant access
            if not any(role in allowed_roles for role in remote_account_roles):
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator