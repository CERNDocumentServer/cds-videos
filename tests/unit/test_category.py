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


import json

from flask import url_for
from flask_security import login_user
from helpers import create_category
from invenio_accounts.models import User
from invenio_search import current_search_client


def test_load_jsonschema_category(api_app, json_headers):
    """Load jsonschema for category."""
    with api_app.test_client() as client:
        res = client.get(
            url_for(
                "invenio_jsonschemas.get_schema",
                schema_path="categories/category-v1.0.0.json",
            ),
            headers=json_headers,
        )

        assert res.status_code == 200


def test_get_category_from_url(
    api_app, db, es, indexer, pidstore, json_headers, category_1
):
    """Load jsonschema for category."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for("invenio_records_rest.catid_list")

    with api_app.test_client() as client:
        res = client.get(url, headers=json_headers)

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["hits"]["hits"]) == 1
        categ = data["hits"]["hits"][0]
        assert categ["metadata"] == category_1


def test_suggest_category_from_url(
    api_app, db, es, indexer, pidstore, json_headers, category_1, category_2
):
    """Load jsonschema for category."""
    current_search_client.indices.refresh()
    with api_app.test_request_context():
        url = url_for("invenio_records_rest.catid_suggest")

    with api_app.test_client() as client:
        # suggest 1
        res = client.get(
            url, headers=json_headers, query_string={"suggest-name": "op", "size": 10}
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["suggest-name"][0]["options"]) == 1
        assert len(data["suggest-name"][0]["options"][0]["_source"]["types"]) == 2
        assert "footage" in data["suggest-name"][0]["options"][0]["_source"]["types"]
        assert "video" in data["suggest-name"][0]["options"][0]["_source"]["types"]

        # suggest 2
        res = client.get(
            url, headers=json_headers, query_string={"suggest-name": "at", "size": 10}
        )

        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))
        assert len(data["suggest-name"][0]["options"]) == 1
        assert len(data["suggest-name"][0]["options"][0]["_source"]["types"]) == 1
        assert "video" in data["suggest-name"][0]["options"][0]["_source"]["types"]


def test_categories_visible_to_their_egroups(
    api_app, db, es, location, indexer, pidstore, users, json_headers
):
    """The restricted categories are listed for their e-groups and admins."""
    egroup = "atlas-readers@cern.ch"
    create_category(
        api_app=api_app,
        db=db,
        data={"name": "open", "types": ["video"], "_record_type": ["video"]},
    )
    create_category(
        api_app=api_app,
        db=db,
        data={
            "name": "atlas",
            "types": ["video"],
            "_record_type": ["video"],
            "_access": {"read": [egroup]},
        },
    )
    datastore = api_app.extensions["security"].datastore
    with db.session.begin_nested():
        role = datastore.create_role(id=egroup, name=egroup)
        datastore.add_role_to_user(db.session.get(User, users[1]), role)
    db.session.commit()
    current_search_client.indices.refresh()
    superadmin = User.query.filter_by(email="superadmin@inveniosoftware.org").one()

    with api_app.test_request_context():
        url = url_for("invenio_records_rest.catid_list")

    def names(user_id=None):
        with api_app.test_client() as client:
            if user_id:
                login_user(db.session.get(User, user_id))
            res = client.get(url, headers=json_headers)
            assert res.status_code == 200
            hits = json.loads(res.data.decode("utf-8"))["hits"]["hits"]
            return sorted(hit["metadata"]["name"] for hit in hits)

    # Anonymous and users outside of the e-group
    assert names() == ["open"]
    assert names(users[0]) == ["open"]
    # Members of the e-group
    assert names(users[1]) == ["atlas", "open"]
    # Super admins
    assert names(superadmin.id) == ["atlas", "open"]
