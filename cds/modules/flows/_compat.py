# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
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

"""Compatibility module for Flask."""

from __future__ import absolute_import

from distutils.version import LooseVersion as V

from pkg_resources import get_distribution

_FLASK_CURRENT_VERSION = V(get_distribution('flask').version)
_FLASK_VERSION_WITH_BUG = V('0.12')


def delete_cached_json_for(request):
    """Delete `_cached_json` attribute for the given request.

    Bug workaround to delete `_cached_json` attribute when using Flask < 0.12.
    More details: https://github.com/pallets/flask/issues/2087

    Note that starting from Flask 1.0, the private `_cached_json` attribute
    has been changed in Flask package, and this code will fail.
    """
    if _FLASK_CURRENT_VERSION < _FLASK_VERSION_WITH_BUG:
        if hasattr(request, '_cached_json'):
            delattr(request, '_cached_json')
