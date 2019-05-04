# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017 CERN.
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

"""CDS fixtures tests."""

from __future__ import absolute_import, print_function

import json

import mock
import pytest
from cds.modules.fixtures.cli import categories as cli_categories
from cds.modules.fixtures.cli import keywords as cli_keywords
from cds.modules.fixtures.cli import licenses as cli_licenses
from cds.modules.fixtures.cli import pages as cli_pages
from cds.modules.fixtures.cli import records as cli_records
from cds.modules.fixtures.cli import \
    sequence_generator as cli_sequence_generator
from click.testing import CliRunner
from invenio_pages import InvenioPages, Page
from invenio_records.models import RecordMetadata
from invenio_sequencegenerator.models import TemplateDefinition


def test_fixture_licenses(app, script_info, db, es, cds_jsonresolver,
                          licenses):
    """Test load category fixtures."""
    assert len(RecordMetadata.query.all()) == 0
    runner = CliRunner()

    class TestRequest(object):
        def json(self):
            return licenses
    return_value = TestRequest()

    with mock.patch('requests.get', return_value=return_value):
        res = runner.invoke(cli_licenses, [], obj=script_info)
    assert res.exit_code == 0
    licenses_db = RecordMetadata.query.all()
    assert len(licenses_db) == 4
    for license in licenses_db:
        assert 'id' in license.json
        assert 'title' in license.json
        assert 'url' in license.json
    ids = set([license.json['id'] for license in licenses_db])
    assert len(ids) == 4
    assert 'CERN' in ids


def test_fixture_keywords(app, script_info, db, es, cds_jsonresolver,
                          cern_keywords):
    """Test load category fixtures."""
    assert len(RecordMetadata.query.all()) == 0
    runner = CliRunner()
    return_value = type('test', (object, ), {
        'text': json.dumps(cern_keywords)}
    )
    with mock.patch('requests.get', return_value=return_value):
        res = runner.invoke(cli_keywords, [], obj=script_info)
    assert res.exit_code == 0
    keywords = RecordMetadata.query.all()
    assert len(keywords) == 4
    for keyword in keywords:
        assert 'input' in keyword.json['suggest_name']
        assert 'name' in keyword.json['suggest_name']['payload']
        assert 'key_id' in keyword.json['suggest_name']['payload']
        assert 'deleted' in keyword.json
        assert 'name' in keyword.json
        assert 'key_id' in keyword.json


def test_fixture_categories(app, script_info, db, es, cds_jsonresolver):
    """Test load category fixtures."""
    assert len(RecordMetadata.query.all()) == 0
    runner = CliRunner()
    res = runner.invoke(cli_categories, [], obj=script_info)
    assert res.exit_code == 0
    categories = RecordMetadata.query.all()
    assert len(categories) == 6
    for category in categories:
        assert 'VIDEO' in category.json['types']


def test_fixture_sequence_generator(app, script_info, db):
    """Test load sequence generator fixtures."""
    TemplateDefinition.query.delete()
    assert len(TemplateDefinition.query.all()) == 0
    runner = CliRunner()
    res = runner.invoke(cli_sequence_generator, [], obj=script_info)
    assert res.exit_code == 0
    templates = TemplateDefinition.query.all()
    assert len(templates) == 2


def test_fixture_pages(app, script_info, db, client):
    """Test load pages fixtures."""
    InvenioPages(app)
    Page.query.delete()
    assert len(Page.query.all()) == 0
    about_response = client.get('/about')
    assert about_response.status_code == 404
    runner = CliRunner()
    res = runner.invoke(cli_pages, [], obj=script_info)
    assert res.exit_code == 0
    pages = Page.query.all()
    assert len(pages) == 7
    about_response = client.get('/about')
    assert about_response.status_code == 200


@pytest.mark.skip(reason='To long due to file download from cernbox')
def test_fixture_records(app, script_info, location, es):
    """Test load demo records."""
    # TODO: once we have a nice subset of test finish the test with more checks
    assert len(RecordMetadata.query.all()) == 0
    runner = CliRunner()
    res = runner.invoke(cli_records, [], obj=script_info)
    assert res.exit_code == 0
    assert len(RecordMetadata.query.all()) > 0
