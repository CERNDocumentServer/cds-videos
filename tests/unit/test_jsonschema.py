# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
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

"""Test jsonschemas."""

from __future__ import absolute_import, print_function

import json
import mock
import pkg_resources
import pytest
import jsonresolver

from jsonresolver import JSONResolver
from jsonref import JsonRef
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonresolver.contrib.jsonschema import ref_resolver_factory
from jsonschema.exceptions import ValidationError
from invenio_records.api import Record


def mock_get_schema(self, path):
    """Mock the ``get_schema`` method of InvenioJSONSchemasState."""
    with open(pkg_resources.resource_filename(
            'cds.modules.records.jsonschemas', path), 'r') as f:
        return json.load(f)


@mock.patch('invenio_jsonschemas.ext.InvenioJSONSchemasState.get_schema',
            mock_get_schema)
def test_base_jsonschema(app):
    """Test base schema."""
    schema = {'$ref': 'http://localhost:5000/schemas/records/base-v1.0.0.json'}

    r1 = Record({'$schema': schema})
    with pytest.raises(ValidationError) as exc_info:
        r1.validate()

    r2 = Record(
        {'$schema': schema,
         'recid': 1,
         '_access': {}
         }
    )
    assert r2.validate() is None


@mock.patch('invenio_jsonschemas.ext.InvenioJSONSchemasState.get_schema',
            mock_get_schema)
def test_video_jsonschema(app):
    """Test video schema."""
    schema = {'$ref':
              'http://localhost:5000/schemas/records/video-v1.0.0.json'}

    app.extensions['invenio-records'].loader_cls = json_loader_factory(
        JSONResolver(plugins=['demo.json_resolver']))

    r1 = Record({'$schema': schema})
    with pytest.raises(ValidationError) as exc_info:
        r1.validate()

    r2 = Record(
        {'$schema': schema,
         'recid': 1,
         '_access': {}
         }
    )
    assert r2.validate() is None
