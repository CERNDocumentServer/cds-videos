# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017, 2020 CERN.
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

"""Test video."""


import json

import mock
import pytest
from celery import states
from flask import url_for
from flask_security import login_user
from helpers import (
    MOCK_TASK_NAMES,
    TestFlow,
    mock_current_user,
    prepare_videos_for_publish,
)
from invenio_accounts.models import User
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.models import RecordMetadata
from invenio_search.engine import dsl
from jsonschema.exceptions import ValidationError
from mock import MagicMock
from six import BytesIO

from cds.modules.deposit.api import (
    Video,
    deposit_video_resolver,
    record_build_url,
    record_video_resolver,
    video_build_url,
    video_resolver,
)
from cds.modules.deposit.indexer import CDSRecordIndexer
from cds.modules.fixtures.video_utils import add_master_to_video
from cds.modules.flows.api import FlowService
from cds.modules.invenio_deposit.search import DepositSearch
from cds.modules.records.api import CDSVideosFilesIterator


def test_video_resolver(api_project):
    """Test vide resolver."""
    (project, video_1, video_2) = api_project
    videos = [
        video_resolver.resolve(video_1["_deposit"]["id"])[1],
        video_resolver.resolve(video_2["_deposit"]["id"])[1],
    ]
    original = [video_1.id, video_2.id]
    original.sort()
    resolved = [videos[0].id, videos[1].id]
    resolved.sort()
    assert original == resolved


def test_video_publish_and_edit(api_project, users):
    """Test video publish and edit."""
    (project, video_1, video_2) = api_project
    video_path_1 = project["videos"][0]["$ref"]
    video_path_2 = project["videos"][1]["$ref"]

    deposit_project_schema = "https://cds.cern.ch/schemas/deposits/records/videos/project/project-v1.0.0.json"
    deposit_video_schema = (
        "https://cds.cern.ch/schemas/deposits/records/videos/video/video-v1.0.0.json"
    )

    record_video_schema = (
        "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json"
    )

    # check video1 is not published
    assert video_1["_deposit"]["status"] == "draft"
    assert video_2["_deposit"]["status"] == "draft"
    assert project["_deposit"]["status"] == "draft"
    # and the schema is a deposit
    assert video_1["$schema"] == deposit_video_schema
    assert video_2["$schema"] == deposit_video_schema
    assert project["$schema"] == deposit_project_schema

    # update video

    # [publish the video 1]
    login_user(User.query.get(users[0]))
    prepare_videos_for_publish([video_1])
    video_1 = video_1.publish()

    project = video_1.project
    (_, record_video_1) = video_1.fetch_published()
    record_video_id_1 = record_video_1["recid"]
    record_path_1 = record_build_url(record_video_id_1)

    # check new link project -> video
    assert video_1["_deposit"]["status"] == "published"
    assert video_2["_deposit"]["status"] == "draft"
    assert project["_deposit"]["status"] == "draft"
    # check the schema is a record
    assert record_video_1["$schema"] == record_video_schema
    assert video_2["$schema"] == deposit_video_schema
    assert project["$schema"] == deposit_project_schema
    # check video recid is inside the list
    assert (
        any(video_ref["$ref"] == record_path_1 for video_ref in project["videos"])
        is True
    )
    # and there is not the old id (when the video was a deposit)
    assert (
        any(video_ref["$ref"] == video_path_1 for video_ref in project["videos"])
        is False
    )
    # and still exists video 2 deposit id
    assert (
        any(video_ref["$ref"] == video_path_2 for video_ref in project["videos"])
        is True
    )

    # [edit the video 1]
    video_1_v2 = record_video_resolver(record_video_1["_deposit"]["pid"]["value"])
    video_1_v2 = video_1_v2.edit()

    # check video1 is not published
    assert video_1_v2["_deposit"]["status"] == "draft"
    assert video_2["_deposit"]["status"] == "draft"
    assert project["_deposit"]["status"] == "draft"
    # check the schema is a record
    assert video_1_v2["$schema"] == deposit_video_schema
    assert video_2["$schema"] == deposit_video_schema
    assert project["$schema"] == deposit_project_schema
    project = video_1_v2.project

    # check video1 v1 recid is NOT inside the list
    assert (
        any(video_ref["$ref"] == record_path_1 for video_ref in project["videos"])
        is False
    )
    # check video1 v2 is inside the list
    video_path_1_v2 = video_build_url(video_1_v2["_deposit"]["id"])
    assert (
        any(video_ref["$ref"] == video_path_1_v2 for video_ref in project["videos"])
        is True
    )


@pytest.mark.parametrize("force", [False, True])
def test_delete_video_not_published(api_project, force):
    """Test video delete when draft."""
    (project, video_1, video_2) = api_project

    project_id = project.id
    video_1_ref = video_1.ref
    video_2_id = video_2.id

    assert project.status == "draft"
    assert video_2.status == "draft"

    video_2.delete(force=force)

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert [{"$ref": video_1_ref}] == project_meta.json["videos"]

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    if force:
        assert video_2_meta is None
    else:
        assert video_2_meta.json is None


@pytest.mark.parametrize("force", [False, True])
def test_delete_video_published(api_project, force, users):
    """Test video delete after published."""
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])

    login_user(User.query.get(users[0]))
    video_2 = video_2.publish()

    project_id = project.id
    video_2_id = video_2.id
    video_2_ref = video_2.ref

    assert project.status == "draft"
    assert video_2.status == "published"

    with pytest.raises(PIDInvalidAction):
        video_2.delete(force=force)

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    assert video_2_meta.json is not None

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert {"$ref": video_2_ref} in project_meta.json["videos"]


def test_video_dumps(db, api_project, video):
    """Test video dump, in particular file dump."""
    (project, video_1, video_2) = api_project
    bucket_id = video_1["_buckets"]["deposit"]
    obj = ObjectVersion.create(
        bucket=bucket_id, key="master.mp4", stream=open(video, "rb")
    )
    slave_1 = ObjectVersion.create(
        bucket=bucket_id, key="slave_1.mp4", stream=open(video, "rb")
    )
    ObjectVersionTag.create(slave_1, "master", str(obj.version_id))
    ObjectVersionTag.create(slave_1, "media_type", "video")
    ObjectVersionTag.create(slave_1, "context_type", "subformat")

    for i in reversed(range(10)):
        slave = ObjectVersion.create(
            bucket=bucket_id,
            key="frame-{0}.jpeg".format(i),
            stream=BytesIO(b"\x00" * 1024),
        )
        ObjectVersionTag.create(slave, "master", str(obj.version_id))
        ObjectVersionTag.create(slave, "media_type", "image")
        ObjectVersionTag.create(slave, "context_type", "frame")

    db.session.commit()

    files = video_1.files.dumps()

    assert len(files) == 1
    files = files[0]  # only one master file

    assert "frame" in files
    assert [f["key"] for f in files["frame"]] == [
        "frame-{}.jpeg".format(i) for i in range(10)
    ]
    assert "subformat" in files
    assert len(files["subformat"]) == 1


@pytest.mark.skip(reason="TO BE CHECKED")
def test_video_delete_with_workflow(api_app, users, api_project, local_file, es):
    """Test publish a project with a workflow."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1["_deposit"]["id"]
    bucket_id = str(video_1.files.bucket.id)

    user_id = "1"
    key = "abc.mp4"
    version_id = str(local_file)

    mock_delete = MagicMock(return_value=None)
    FlowService.delete = mock_delete

    headers = [("Content-Type", "application/json")]
    payload = json.dumps(dict(somekey="somevalue"))
    with api_app.test_request_context(headers=headers, data=payload):
        flow = TestFlow(
            deposit_id=video_1_depid,
            name="TestFlow",
            payload={
                "deposit_id": video_1_depid,
                "bucket_id": bucket_id,
                "version_id": version_id,
                "key": key,
            },
            user_id=user_id,
        )
        # db.session.add(flow.model)
        flow.run()
    db.session.commit()

    video_1 = deposit_video_resolver(video_1_depid)
    video_1.delete()
    assert mock_delete.called is True


def test_video_record_schema(app, db, api_project):
    """Test video record schema."""
    (project, video_1, video_2) = api_project
    assert video_1.record_schema == Video.get_record_schema()


@mock.patch("flask_login.current_user", mock_current_user)
@mock.patch("cds.modules.flows.api.Flow", TestFlow)
@mock.patch("cds.modules.flows.views.Flow", TestFlow)
@pytest.mark.skip(reason="TO BE CHECKED")
def test_video_flows_on_workflow(
    api_app, db, es, api_project, bucket, json_headers, local_file, access_token
):
    """Test deposit flows."""
    (project, video_1, video_2) = api_project
    project_depid = project["_deposit"]["id"]
    video_1_depid = video_1["_deposit"]["id"]
    bucket_id = str(bucket.id)
    version_id = str(local_file)
    key = "TEST.mp4"
    db.session.add(bucket)

    with api_app.test_request_context():
        url = url_for("cds_flows.flow_list", access_token=access_token)

    with api_app.test_client() as client:
        # run workflow
        resp = client.post(
            url,
            headers=json_headers,
            data=json.dumps(
                {
                    "deposit_id": video_1_depid,
                    "version_id": version_id,
                    "bucket_id": bucket_id,
                    "key": key,
                }
            ),
        )
        assert resp.status_code == 500
        # run again workflow
        resp = client.post(
            url,
            headers=json_headers,
            data=json.dumps(
                {
                    "deposit_id": video_1_depid,
                    "version_id": version_id,
                    "bucket_id": bucket_id,
                    "key": key,
                }
            ),
        )
        assert resp.status_code == 500
        # resolve deposit and flows
        deposit = deposit_video_resolver(video_1_depid)

        flows = get_all_deposit_flows(deposit["_deposit"]["id"])
        # check flows
        assert len(flows) == 2

        assert flows[0].payload["deposit_id"] == video_1_depid
        assert flows[1].payload["deposit_id"] == video_1_depid
        # check computed status

        status = get_tasks_status_grouped_by_task_name(flows)

        assert status["sse_simple_add"] == states.SUCCESS
        assert status["sse_failing_task"] == states.FAILURE

        # check if the states are inside the deposit
        res = client.get(
            url_for("invenio_deposit_rest.video_item", pid_value=video_1_depid),
            headers=json_headers,
        )
        assert res.status_code == 200
        data = json.loads(res.data.decode("utf-8"))["metadata"]
        assert data["_cds"]["state"]["sse_simple_add"] == states.SUCCESS
        assert data["_cds"]["state"]["sse_failing_task"] == states.FAILURE

        # run indexer
        ids = PersistentIdentifier.query.filter(
            PersistentIdentifier.status == PIDStatus.REGISTERED,
        )
        obj_ids = [str(p.object_uuid) for p in ids]
        RecordIndexer().bulk_index(iter(obj_ids))
        RecordIndexer().process_bulk_queue()
        current_search_client.indices.refresh()
        # check elasticsearch video_1 state
        resp = client.get(
            url_for(
                "invenio_deposit_rest.video_list",
                q="_deposit.id:{0}".format(video_1_depid),
                access_token=access_token,
            ),
            headers=json_headers,
        )
        assert resp.status_code == 200
        data = json.loads(resp.data.decode("utf-8"))
        status = data["hits"]["hits"][0]["metadata"]["_cds"]["state"]
        assert status["sse_simple_add"] == states.SUCCESS
        assert status["sse_failing_task"] == states.FAILURE
        # check elasticsearch project state
        resp = client.get(
            url_for(
                "invenio_deposit_rest.video_list",
                q="_deposit.id:{0}".format(project_depid),
                access_token=access_token,
            ),
            headers=json_headers,
        )
        assert resp.status_code == 200
        data = json.loads(resp.data.decode("utf-8"))
        status = data["hits"]["hits"][0]["metadata"]["_cds"]["state"]
        assert status["sse_simple_add"] == states.SUCCESS
        assert status["sse_failing_task"] == states.FAILURE


def test_video_publish_with_no_category(api_project, users):
    """Test video publish if category is not set."""
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    # test: no category in project
    del project["category"]
    assert "type" in project
    project.commit()
    db.session.commit()
    login_user(User.query.get(users[0]))
    with pytest.raises(ValidationError):
        video_1.publish()


def test_video_publish_with_no_type(api_project, users):
    """Test video publish with no type."""
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    video_1_depid = video_1["_deposit"]["id"]
    # test: no type in project
    del project["type"]
    assert "category" in project
    project.commit()
    db.session.commit()
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    with pytest.raises(ValidationError):
        video_1.publish()


def test_video_publish_with_category_and_type(api_project, users):
    """Test video publish with category and type."""
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    video_1_depid = video_1["_deposit"]["id"]
    # test with category + type
    assert "type" in project
    assert "category" in project
    project.commit()
    db.session.commit()
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    video_1.publish()
    assert video_1["_deposit"]["status"] == "published"


@pytest.mark.skip(reason="TO BE CHECKED")
def test_video_keywords(es, api_project, keyword_1, keyword_2, users):
    """Tet video keywords."""
    (project, video_1, video_2) = api_project
    # login owner
    login_user(User.query.filter_by(id=users[0]).first())

    assert video_1["keywords"] == []

    # try to add keywords
    video_1.add_keyword(keyword_1)
    video_1.add_keyword(keyword_2)
    video_1.add_keyword(keyword_1)
    assert video_1["keywords"] == [
        {"$ref": keyword_1.ref},
        {"$ref": keyword_2.ref},
    ]
    video_1.commit()
    db.session.commit()
    CDSRecordIndexer().index(video_1)
    current_search_client.indices.refresh()

    # check elasticsearch
    result = (
        DepositSearch()
        .filter(dsl.Q("match", **{"_deposit.id": video_1["_deposit"]["id"]}))
        .params(version=True)
        .execute()
        .to_dict()["hits"]["hits"][0]
    )
    kw_result = {k["key_id"]: k["name"] for k in result["_source"]["keywords"]}
    kw_expect = {k["key_id"]: k["name"] for k in [keyword_1, keyword_2]}
    assert kw_expect == kw_result

    # try to remove a key
    video_1.remove_keyword(keyword_1)
    assert video_1["keywords"] == [
        {"$ref": keyword_2.ref},
    ]
    video_1.commit()
    db.session.commit()
    CDSRecordIndexer().index(video_1)
    current_search_client.indices.refresh()

    # check elasticsearch
    result = (
        DepositSearch()
        .filter(dsl.Q("match", **{"_deposit.id": video_1["_deposit"]["id"]}))
        .params(version=True)
        .execute()
        .to_dict()["hits"]["hits"][0]
    )
    kw_result = {k["key_id"]: k["name"] for k in result["_source"]["keywords"]}
    kw_expect = {k["key_id"]: k["name"] for k in [keyword_2]}
    assert kw_expect == kw_result


@mock.patch("flask_login.current_user", mock_current_user)
@pytest.mark.skip(reason="TO BE CHECKED")
def test_deposit_vtt_tags(api_app, db, api_project, users):
    """Test VTT tag generation."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1["_deposit"]["id"]

    # insert a master file inside the video
    add_master_to_video(
        video_deposit=video_1,
        filename="test.mp4",
        stream=BytesIO(b"1234"),
        video_duration="15",
    )
    # try to insert a new vtt object
    obj = ObjectVersion.create(
        video_1._bucket, key="test_fr.vtt", stream=BytesIO(b"hello")
    )
    # publish the video
    prepare_videos_for_publish([video_1])
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    video_1 = video_1.publish()

    # check tags
    check_object_tags(
        obj,
        video_1,
        content_type="vtt",
        media_type="subtitle",
        context_type="subtitle",
        language="fr",
    )

    # edit the video
    video_1 = video_1.edit()

    # try to delete the old vtt file and substitute with a new one
    video_1 = deposit_video_resolver(video_1_depid)
    ObjectVersion.delete(bucket=video_1._bucket, key=obj.key)
    obj2 = ObjectVersion.create(
        video_1._bucket, key="test_en.vtt", stream=BytesIO(b"hello")
    )

    # publish again the video
    video_1 = video_1.publish()

    # check tags
    check_object_tags(
        obj2,
        video_1,
        content_type="vtt",
        media_type="subtitle",
        context_type="subtitle",
        language="en",
    )

    # edit a re-published video
    video_1 = video_1.edit()

    # add a new vtt file
    obj3 = ObjectVersion.create(
        video_1._bucket, key="test_it.vtt", stream=BytesIO(b"hello")
    )

    # publish again the video
    video_1 = video_1.publish()

    # check tags
    check_object_tags(
        obj3,
        video_1,
        content_type="vtt",
        media_type="subtitle",
        context_type="subtitle",
        language="it",
    )


@mock.patch("flask_login.current_user", mock_current_user)
def test_deposit_poster_tags(api_app, db, api_project, users):
    """Test poster tag generation."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1["_deposit"]["id"]
    master_video_filename = "test.mp4"
    poster_filename = "poster.jpg"
    poster_filename2 = "poster.png"

    # insert a master file inside the video
    add_master_to_video(
        video_deposit=video_1,
        filename=master_video_filename,
        stream=BytesIO(b"1234"),
        video_duration="15",
    )
    # try to insert a new vtt object
    obj = ObjectVersion.create(
        video_1._bucket, key=poster_filename, stream=BytesIO(b"hello")
    )
    # publish the video
    prepare_videos_for_publish([video_1])
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    video_1 = video_1.publish()

    # check tags
    check_object_tags(
        obj, video_1, content_type="jpg", context_type="poster", media_type="image"
    )

    # edit the video
    video_1 = video_1.edit()

    # try to delete the old poster frame and substitute with a new one
    video_1 = deposit_video_resolver(video_1_depid)
    ObjectVersion.delete(bucket=video_1._bucket, key=obj.key)
    obj2 = ObjectVersion.create(
        video_1._bucket, key=poster_filename2, stream=BytesIO(b"hello")
    )

    # publish again the video
    video_1 = video_1.publish()

    # check tags
    check_object_tags(
        obj2, video_1, content_type="png", context_type="poster", media_type="image"
    )


@mock.patch("flask_login.current_user", mock_current_user)
@pytest.mark.skip(reason="TO BE CHECKED")
def test_deposit_smil_tag_generation(api_app, db, api_project, users):
    """Test AVCWorkflow receiver."""

    def check_smil(video):
        _, record = video.fetch_published()
        master = CDSVideosFilesIterator.get_master_video_file(record)
        playlist = master["playlist"]
        assert playlist[0]["key"] == "{}.smil".format(record["report_number"][0])
        assert playlist[0]["content_type"] == "smil"
        assert playlist[0]["context_type"] == "playlist"
        assert playlist[0]["media_type"] == "text"
        assert playlist[0]["tags"]["master"] == master["version_id"]

        # check bucket dump is done correctly
        master_video = CDSVideosFilesIterator.get_master_video_file(video)
        assert master_video["version_id"] != master["version_id"]

    project, video_1, video_2 = api_project
    video_1_depid = video_1["_deposit"]["id"]

    # insert a master file inside the video
    add_master_to_video(
        video_deposit=video_1,
        filename="test.mp4",
        stream=BytesIO(b"1234"),
        video_duration="15s",
    )
    # publish the video
    prepare_videos_for_publish([video_1])
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    video_1 = video_1.publish()

    # check smil
    check_smil(video_1)

    # edit the video
    video_1 = video_1.edit()

    # publish again the video
    video_1 = video_1.publish()

    # check smil
    check_smil(video_1)


def test_video_name_after_publish(api_app, db, api_project, users):
    project, video_1, video_2 = api_project
    video_1_depid = video_1["_deposit"]["id"]
    master_video_filename = "test.mp4"

    # insert a master file inside the video
    add_master_to_video(
        video_deposit=video_1,
        filename=master_video_filename,
        stream=BytesIO(b"1234"),
        video_duration="15",
    )

    # publish the video
    prepare_videos_for_publish([video_1])
    video_1 = deposit_video_resolver(video_1_depid)
    login_user(User.query.get(users[0]))
    video_1 = video_1.publish()

    _, record = video_1.fetch_published()
    master = CDSVideosFilesIterator.get_master_video_file(record)
    assert master["key"] == "{}.mp4".format(record["report_number"][0])


def check_object_tags(obj, video, **tags):
    """Check tags on an ObjectVersion (i.e. on DB and deposit/record dump)."""
    assert obj.get_tags() == tags
    for dump in [
        [d for d in files if d["key"] == obj.key][0]
        for files in [video._get_files_dump(), video.fetch_published()[1]["_files"]]
    ]:
        assert dump["content_type"] == tags["content_type"]
        assert dump["context_type"] == tags["context_type"]
        assert dump["media_type"] == tags["media_type"]
        assert dump["tags"] == {
            t: tags[t] for t in tags if t not in ["context_type", "media_type"]
        }
