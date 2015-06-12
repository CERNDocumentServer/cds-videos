# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Base class for the personal collection boxes.

The `build` method from all boxes should return the same structure, containing
at least:

    {
        'header': {
            'title': 'My awesome box'
            }
        'items': [{...}, {...}]
        'footer': {
            'label': 'Show me all',
            'link': 'https://......'
        },
        '_settings': {....} # Same as in the DB

    }
"""


class BoxBase(type):

    """Metaclass for all boxes."""

    def __new__(mcs, *args, **kwargs):
        """Set needed class attributes if they don't exist."""
        if '__displayname__' not in args[2]:
            args[2]['__displayname__'] = args[0].lower().replace('box', '')
        if '__template__' not in args[2]:
            args[2]['__template__'] = args[0].lower().replace('box', '')
        if '__boxname__' not in args[2]:
            args[2]['__boxname__'] = args[0].lower().replace('box', '')

        return super(BoxBase, mcs).__new__(mcs, args[0], args[1], args[2])
