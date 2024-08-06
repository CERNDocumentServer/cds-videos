# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
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

"""Test cds keyword."""


import json

from flask import url_for
from invenio_search import current_search_client


def test_load_jsonschema_category(api_app, json_headers):
    """Load jsonschema for keyword."""
    with api_app.test_client() as client:
        res = client.get(
            url_for(
                "invenio_jsonschemas.get_schema",
                schema_path="keywords/keyword-v1.0.0.json",
            ),
            headers=json_headers,
        )

        assert res.status_code == 200


def test_get_keyword_from_url(
    api_app, db, es, indexer, pidstore, json_headers, keyword_1, keyword_3_deleted
):
    """Load jsonschema for keyword."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for("invenio_records_rest.kwid_list")

    with api_app.test_client() as client:
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["hits"]["hits"]) == 1
        keyw = data["hits"]["hits"][0]
        assert keyw["metadata"] == keyword_1


def test_suggest_keyword_from_url(
    api_app,
    db,
    es,
    indexer,
    pidstore,
    json_headers,
    keyword_1,
    keyword_2,
    keyword_3_deleted,
):
    """Load jsonschema for keyword."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for("invenio_records_rest.kwid_suggest")

    with api_app.test_client() as client:
        # suggest 1
        res = client.get(
            url,
            headers=json_headers,
            query_string={"suggest-name": keyword_2["name"][0:3], "size": 10},
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["suggest-name"][0]["options"]) == 1
        name = data["suggest-name"][0]["options"][0]["_source"]["name"]
        assert name == keyword_2["name"]
        key = data["suggest-name"][0]["options"][0]["_source"]["key_id"]
        assert key in keyword_2["key_id"]

        # suggest 2
        res = client.get(
            url,
            headers=json_headers,
            query_string={"suggest-name": "no-exist", "size": 10},
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["suggest-name"][0]["options"]) == 0
