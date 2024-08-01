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

"""Test deposit."""

from __future__ import absolute_import, print_function

import json

import mock
from flask import current_app, request, url_for
from flask_security import login_user
from helpers import check_deposit_record_files, check_deposit_record_files_not_publsihed
from invenio_accounts.models import User
from invenio_files_rest.models import (
    Bucket,
    FileInstance,
    ObjectVersion,
    ObjectVersionTag,
)

from cds.modules.deposit.api import CDSDeposit, Project
from cds.modules.deposit.views import to_links_js


def test_deposit_link_factory_has_bucket(
    api_app,
    db,
    es,
    users,
    location,
    json_headers,
    json_partial_project_headers,
    json_partial_video_headers,
    video_deposit_metadata,
    project_deposit_metadata,
):
    """Test bucket link factory retrieval of a bucket."""
    with api_app.test_client() as client:
        login_user(User.query.get(users[0]))

        # Test links for project
        res = client.post(
            url_for("invenio_deposit_rest.project_list"),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers,
        )
        assert res.status_code == 201
        data = json.loads(res.data.decode("utf-8"))
        links = data["links"]
        pid = data["metadata"]["_deposit"]["id"]
        assert "bucket" in links
        assert links["html"] == current_app.config["DEPOSIT_UI_ENDPOINT"].format(
            host=request.host, scheme=request.scheme, pid_value=pid
        )

        # Test links for videos
        res = client.post(
            url_for("invenio_deposit_rest.video_list"),
            data=json.dumps(
                {
                    "_project_id": pid,
                }
            ),
            headers=json_partial_video_headers,
        )

        assert res.status_code == 201
        data = json.loads(res.data.decode("utf-8"))
        links = data["links"]
        pid = data["metadata"]["_deposit"]["id"]
        assert "bucket" in links
        assert links["html"] == current_app.config["DEPOSIT_UI_ENDPOINT"].format(
            host=request.host, scheme=request.scheme, pid_value=pid
        )


def test_links_filter(app, es, location, deposit_metadata):
    """Test Jinja to_links_js filter."""
    assert to_links_js(None) == []
    deposit = Project.create(deposit_metadata)
    links = to_links_js(deposit.pid, deposit)
    assert all(
        [
            key in links
            for key in ["self", "edit", "publish", "bucket", "files", "html", "discard"]
        ]
    )
    self_url = links["self"]
    assert links["discard"] == self_url + "/actions/discard"
    assert links["edit"] == self_url + "/actions/edit"
    assert links["publish"] == self_url + "/actions/publish"
    assert links["files"] == self_url + "/files"
    links_type = to_links_js(deposit.pid, deposit, "project")
    self_url_type = links_type["self"]
    assert links_type["discard"] == self_url_type + "/actions/discard"
    assert links_type["edit"] == self_url_type + "/actions/edit"
    assert links_type["publish"] == self_url_type + "/actions/publish"
    assert links_type["files"] == self_url_type + "/files"
    # TODO: CHECK
    # with app.test_client() as client:
    #     data = client.get(links_type['html']).get_data().decode('utf-8')
    #     for key in links_type:
    #         assert links_type[key] in data


def test_publish_process_files(api_app, db, location):
    """Test _process_files changing master tags on bucket snapshots."""
    deposit = CDSDeposit.create(
        dict(
            date="1/2/3",
            category="cat",
            type="type",
            title=dict(title="title"),
            report_number=["1234"],
            videos=[],
        ),
        bucket_location="videos",
    )

    # deposit has no files, so _process_files must yield None
    with deposit._process_files(None, dict()) as data:
        assert data is None
    bucket = deposit.files.bucket
    master_obj = ObjectVersion.create(
        bucket=bucket, key="master", _file_id=FileInstance.create()
    )
    number_of_slaves = 10
    for i in range(number_of_slaves):
        slave_obj = ObjectVersion.create(
            bucket=bucket, key="{0}.mp4".format(i + 1), _file_id=FileInstance.create()
        )
        ObjectVersionTag.create(slave_obj, "master", str(master_obj.version_id))
        ObjectVersionTag.create(slave_obj, "media_type", "video")
        ObjectVersionTag.create(slave_obj, "context_type", "subformat")
    assert Bucket.query.count() == 1
    with deposit._process_files(None, dict(_buckets=dict())):
        # the snapshot bucket must have been created
        assert Bucket.query.count() == 2
        for bucket in Bucket.query.all():
            master_version = [
                str(obj.version_id)
                for obj in bucket.objects
                if "master" not in obj.get_tags()
            ][0]
            # the master of each slave must be in the same bucket
            for obj in bucket.objects:
                if str(obj.version_id) != master_version:
                    assert obj.get_tags()["master"] == master_version
                    assert obj.get_tags()["media_type"] == "video"
                    assert obj.get_tags()["context_type"] == "subformat"


def test_deposit_prepare_edit(api_app, db, location, project_deposit_metadata, users):
    """Test deposit prepare edit."""
    # create new deposit
    project_deposit_metadata["report_number"] = ["123"]
    deposit = CDSDeposit.create(project_deposit_metadata, bucket_location=location.name)
    assert deposit.is_published() is False
    assert deposit.has_record() is False
    # insert objects inside the deposit
    ObjectVersion.create(deposit.files.bucket, "obj_1").set_location(
        "mylocation1", 1, "mychecksum1"
    )
    ObjectVersion.create(deposit.files.bucket, "obj_2").set_location(
        "mylocation2", 1, "mychecksum2"
    )
    ObjectVersion.create(deposit.files.bucket, "obj_3").set_location(
        "mylocation3", 1, "mychecksum3"
    )
    obj_4 = ObjectVersion.create(deposit.files.bucket, "obj_4").set_location(
        "mylocation4", 1, "mychecksum4"
    )

    # publish
    login_user(User.query.get(users[0]))
    deposit = deposit.publish()
    _, record = deposit.fetch_published()
    assert deposit.is_published() is True
    assert deposit.has_record() is True
    # check record bucket is locked
    files = ["obj_1", "obj_2", "obj_3", "obj_4"]
    check_deposit_record_files(deposit, files, record, files)

    # edit
    deposit = deposit.edit()
    assert deposit.is_published() is False
    assert deposit.has_record() is True
    # check the situation
    # check_deposit_record_files(deposit, files, record, files)

    # add a new object
    ObjectVersion.create(deposit.files.bucket, "obj_new").set_location(
        "mylocation_new", 1, "mychecksum"
    )
    # modify obj_1
    ObjectVersion.create(deposit.files.bucket, "obj_1").set_location(
        "mylocation2.1", 1, "mychecksum2.1"
    )
    # delete obj_3
    ObjectVersion.delete(deposit.files.bucket, "obj_3")
    # remove obj_4
    obj_4.remove()

    # check deposit and record
    edited_files = ["obj_1", "obj_2", "obj_new"]
    check_deposit_record_files_not_publsihed(deposit, edited_files, record, files)

    # publish again
    deposit = deposit.publish()
    assert deposit.is_published() is True
    assert deposit.has_record() is True
    check_deposit_record_files(deposit, edited_files, record, edited_files)
