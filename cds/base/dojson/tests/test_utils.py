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

from cds.base.dojson.utils import for_each_squash
from dojson.utils import filter_values


def test_for_each_squash():
    """Check if for_each_squash works correctly"""

    @for_each_squash
    @filter_values
    def field(self, key, value):
        return {
            'a': value.get('1'),
            'b': value.get('2')
        }

    squashed = field(None, None, {'1': 'foo', '2': 'bar'})
    assert squashed == {'a': 'foo', 'b': 'bar'}

    squashed = field(None, None, [{'1': 'foo'}, {'2': 'bar'}])
    assert squashed == {'a': 'foo', 'b': 'bar'}

    squashed = field(None, None, [{'1': 'foo', '2': 'bar2'}, {'2': 'bar'}])
    assert squashed == {'a': 'foo', 'b': ['bar2', 'bar']}


test_for_each_squash()  # TODO remove this when joined with proper testsuite