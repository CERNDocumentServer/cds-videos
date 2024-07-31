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

"""Test cds category."""

from __future__ import absolute_import, print_function

import json

from flask import url_for
from invenio_search import current_search_client


def test_load_jsonschema_category(api_app, json_headers):
    """Load jsonschema for category."""
    with api_app.test_client() as client:
        res = client.get(
            url_for('invenio_jsonschemas.get_schema',
                    schema_path='categories/category-v1.0.0.json'),
            headers=json_headers)

        assert res.status_code == 200


def test_get_category_from_url(
        api_app, db, es, indexer, pidstore, json_headers, category_1
):
    """Load jsonschema for category."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for('invenio_records_rest.catid_list')

    with api_app.test_client() as client:
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['hits']['hits']) == 1
        categ = data['hits']['hits'][0]
        assert categ['metadata'] == category_1


def test_suggest_category_from_url(
        api_app, db, es, indexer, pidstore, json_headers, category_1,
        category_2
):
    """Load jsonschema for category."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for('invenio_records_rest.catid_suggest')

    with api_app.test_client() as client:
        # suggest 1
        res = client.get(
            url,
            headers=json_headers,
            query_string={'suggest-name': 'op', 'size': 10}
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['suggest-name'][0]['options']) == 1
        assert len(data[
            'suggest-name'][0]['options'][0]['payload']['types']) == 2
        assert 'footage' in data[
            'suggest-name'][0]['options'][0]['payload']['types']
        assert 'video' in data[
            'suggest-name'][0]['options'][0]['payload']['types']

        # suggest 2
        res = client.get(
            url,
            headers=json_headers,
            query_string={'suggest-name': 'at', 'size': 10}
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode('utf-8'))
        assert len(data['suggest-name'][0]['options']) == 1
        assert len(data[
            'suggest-name'][0]['options'][0]['payload']['types']) == 1
        assert 'video' in data[
            'suggest-name'][0]['options'][0]['payload']['types']
