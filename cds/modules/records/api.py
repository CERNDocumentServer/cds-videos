# -*- coding: utf-8 -*-
#
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

"""Record API."""

from __future__ import absolute_import, print_function

import uuid
import os

from invenio_records.api import Record
from invenio_jsonschemas import current_jsonschemas

from .minters import kwid_minter


class Keyword(Record):

    """Define API for a keywords."""

    _schema = 'keywords/keyword-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a keyword."""
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)

        key_id = data.get('key_id', None)
        name = data.get('name', None)
        data.setdefault('deleted', False)

        if not id_:
            id_ = uuid.uuid4()
            kwid_minter(id_, data)

        data['suggest_name'] = {
            'input': name,
            'payload': {'key_id': key_id, 'name': name},
        }
        return super(Keyword, cls).create(data=data, id_=id_, **kwargs)

    @property
    def ref(self):
        """Get the url."""
        return Keyword.get_ref(self['key_id'])

    @classmethod
    def get_id(cls, ref):
        """Get the ID from the reference."""
        return os.path.basename(ref)

    @classmethod
    def get_ref(cls, id_):
        """Get reference from an ID."""
        return 'https://cds.cern.ch/api/keywords/{0}'.format(str(id_))
