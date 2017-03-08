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

from flask import g
from flask_principal import RoleNeed, UserNeed
from cds.modules.records.search import CERNRecordsSearch


def mock_provides(needs):
    """Mock user provides."""
    g.identity = lambda: None
    g.identity.provides = needs


def test_es_filter(users):
    """Test query filter based on CERN groups."""
    mock_provides([UserNeed('test@test.ch'), RoleNeed('groupX')])
    assert CERNRecordsSearch().to_dict()['query']['bool']['filter'] == [
        {'bool': {'filter': [{'bool': {
            'should': [
                {'missing': {'field': '_access.read'}},
                {'terms': {'_access.read': ['test@test.ch', 'groupX']}},
                {'terms': {'_access.update': ['test@test.ch', 'groupX']}},
                {'match': {'_deposit.created_by': 0}}
            ]
        }}]}}
    ]
