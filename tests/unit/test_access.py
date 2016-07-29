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

import uuid

from cds.modules.access.access_control import cern_read_factory
from flask import g
from flask_principal import RoleNeed, UserNeed
from invenio_records.api import Record
from cds.modules.access.access_control import CERNRecordsSearch


def mock_provides(needs):
    """Mock user provides."""
    g.identity = lambda: None
    g.identity.provides = needs


def test_record_access(db):
    """Test access control for search."""
    mock_provides([UserNeed('test@test.ch'), RoleNeed('groupX')])

    def check_record(json, allowed=True):
        # Create uuid
        id = uuid.uuid4()

        # Create record
        rec = type('obj', (object,), {'id': id})
        Record.create(json, id_=id)

        # Check permission factory
        factory = cern_read_factory(rec)
        assert factory.can() if allowed else not factory.can()

    # Check test records
    check_record({'foo': 'bar'})
    check_record({'_access': {'read': ['test@test.ch', 'groupA', 'groupB']}})
    check_record({'_access': {'read': ['test2@test2.ch', 'groupC']}}, False)
    check_record({'_access': {'read': ['groupX']}})
    check_record({'_access': {'read': ['test@test.ch', 'groupA', 'groupB']}})
    check_record({'_access': {'read': []}})


def test_es_filter():
    """Test query filter based on CERN groups."""
    mock_provides([UserNeed('test@test.ch'), RoleNeed('groupX')])
    assert CERNRecordsSearch().to_dict()['query']['bool']['filter'] == [
        {'bool': {'filter': [{'bool': {
            'should': [
                {'missing': {'field': '_access.read'}},
                {'terms': {'_access.read': ['test@test.ch', 'groupX']}}
            ]
        }}]}}
    ]
