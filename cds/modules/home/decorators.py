# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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


"""CDS frontpage decorators."""

from __future__ import absolute_import, print_function

from functools import wraps

from flask import session
from flask_login import current_user
from invenio_cache import current_cache


def has_flashes_or_authenticated_user():
    """Return True if there are pending flashes or user is authenticated."""
    return '_flashes' in session or current_user.is_authenticated


def cached_unless_authenticated_or_flashes(timeout=50, key_prefix='default'):
    """Cache anonymous traffic."""
    def caching(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_fun = current_cache.cached(
                timeout=timeout, key_prefix=key_prefix,
                unless=has_flashes_or_authenticated_user)
            return cache_fun(f)(*args, **kwargs)
        return wrapper
    return caching
