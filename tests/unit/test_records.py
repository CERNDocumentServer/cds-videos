# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017, 2018 CERN.
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

"""Test records."""


import json
import re
from functools import partial

import mock
import pytest
from flask import url_for
from flask_security import login_user
from helpers import assert_hits_len, get_files_metadata
from invenio_accounts.models import User
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_search import current_search_client

from cds.modules.records.views import serialize_record


def test_records_ui_export(app, project_published, video_record_metadata):
    """Test view."""
    (project, video_1, video_2) = project_published
    # index a (update) video
    _, record_video = video_1.fetch_published()
    record_video.update(**video_record_metadata)
    record_video.commit()
    db.session.commit()
    pid = project["_deposit"]["pid"]["value"]
    vid = video_1["_deposit"]["pid"]["value"]

    url_no_existing_exporter = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=pid, format="blabla"
    )
    url_not_valid_type_record = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=pid, format="smil"
    )
    url_valid_smil = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=vid, format="smil"
    )
    url_valid_vtt = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=vid, format="vtt"
    )
    url_valid_json = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=pid, format="json"
    )
    url_valid_drupal = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=vid, format="drupal"
    )
    url_valid_drupal_project = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=pid, format="drupal"
    )
    url_valid_datacite_video = partial(
        url_for, "invenio_records_ui.recid_export", pid_value=vid, format="dcite"
    )

    def get_pre(data):
        data = data.decode("utf-8")
        data_start = data.find("<pre>") + 5
        data_end = data.find("</pre>", data_start)
        return data[data_start:data_end]

    def check_url(partial_url, status_code):
        res = client.get(partial_url(), follow_redirects=True)
        res_raw = client.get(partial_url(raw=True), follow_redirects=True)
        assert res.status_code == status_code
        assert res_raw.status_code == status_code
        return res.data

    with app.test_request_context():
        with app.test_client() as client:
            with pytest.raises(ValueError):
                check_url(url_no_existing_exporter, 404)
            check_url(url_not_valid_type_record, 400)

            data = check_url(url_valid_smil, 200)
            assert get_pre(data).startswith("&lt;smil&gt;")

            data = check_url(url_valid_vtt, 200)
            assert "WEBVTT" in data.decode("utf-8")

            check_url(url_valid_json, 200)

            data = check_url(url_valid_drupal, 200)
            assert get_pre(data).startswith("{")

            data = check_url(url_valid_drupal_project, 200)
            assert get_pre(data) == "{}"

            data = check_url(url_valid_datacite_video, 200)
            assert get_pre(data).startswith("&lt;?xml version=")


def test_records_rest(
    api_app,
    users,
    es,
    api_project_published,
    vtt_headers,
    datacite_headers,
    json_headers,
    smil_headers,
    drupal_headers,
    extra_metadata,
    _deposit_metadata,
    current_year,
):
    """Test view."""
    indexer = RecordIndexer()
    (project, video_1, video_2) = api_project_published
    pid, record_project = project.fetch_published()
    vid, record_video = video_1.fetch_published()
    bucket_id = str(video_1["_buckets"]["deposit"])

    # index project
    project.indexer.index(record_project)
    # index video
    record_video["_files"] = get_files_metadata(bucket_id)
    record_video["_deposit"].update(_deposit_metadata)
    record_video.update(extra_metadata)
    record_video.commit()
    indexer.index(record_video)
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        login_user(db.session.get(User, users[0]))
        url = url_for("invenio_records_rest.recid_item", pid_value=pid.pid_value)
        url2 = url_for("invenio_records_rest.recid_item", pid_value=vid.pid_value)

        # try get json
        res = client.get(url, headers=json_headers)
        assert res.status_code == 200
        project_dict = json.loads(res.data.decode("utf-8"))
        assert project_dict["metadata"]["_deposit"]["id"] == project["_deposit"]["id"]

        res = client.get(url2, headers=json_headers)
        assert res.status_code == 200
        video_dict = json.loads(res.data.decode("utf-8"))
        assert video_dict["metadata"]["title"]["title"] == "My <b>english</b> title"
        expect_desc = "in tempor reprehenderit enim eiusmod <b><i>html</i></b>"
        assert video_dict["metadata"]["description"] == expect_desc

        # try get smil
        res = client.get(url, headers=smil_headers)
        assert res.status_code == 400

        res = client.get(url2, headers=smil_headers)
        assert res.status_code == 200

        # try get vtt
        res = client.get(url, headers=vtt_headers)
        assert res.status_code == 400

        res = client.get(url2, headers=vtt_headers)
        assert res.status_code == 200

        # try get drupal
        report_number = "CERN-MOVIE-{0}-1-1".format(current_year)
        file_frame = "http://cds.cern.ch/api/files/123/frame-1.jpg"
        with mock.patch(
            "cds.modules.records.api.CDSFileObject._link", return_value=file_frame
        ):
            res = client.get(url2, headers=drupal_headers)
            # test legacy api/mediaexport url
            legacy_url = "/mediaexport?id={id}".format(id=report_number)
            assert client.get(legacy_url, follow_redirects=False).status_code == 301
            res_legacy = client.get(legacy_url, follow_redirects=True)

        assert res.status_code == 200
        assert res_legacy.status_code == 200
        drupal = json.loads(res.data.decode("utf-8"))
        thumbnail = "http://cds.cern.ch/api/files/123/frame-1.jpg"
        expected = {
            "entries": [
                {
                    "entry": {
                        "caption_en": "in tempor reprehenderit enim "
                        "eiusmod <b><i>html</i></b>",
                        "caption_fr": "france caption",
                        "copyright_date": "2017",
                        "copyright_holder": "CERN",
                        "creation_date": "2017-03-02",
                        "directors": "paperone, pluto",
                        "entry_date": "2017-09-25",
                        "id": report_number,
                        "keywords": "keyword1, keyword2",
                        "license_body": "GPLv2",
                        "license_url": "http://license.cern.ch",
                        "producer": "nonna papera, zio paperino",
                        "record_id": "1",
                        "thumbnail": thumbnail,
                        "title_en": "My english title",
                        "title_fr": "My french title",
                        "type": "360 video",
                        "video_length": "00:01:00",
                        # TODO: harmonize links URLs creation
                        "links": {
                            "240p": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                            "original": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                            "self": "http://localhost/record/1",
                            "thumbnail": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                        },
                    }
                }
            ]
        }
        assert expected == drupal
        drupal_legacy = json.loads(res_legacy.data.decode("utf-8"))
        assert expected == drupal_legacy

        # try get datacite
        res = client.get(url2, headers=datacite_headers)
        assert res.status_code == 200
        assert res.data.decode("utf-8").startswith("<?xml version=")

    # test corner cases
    del record_video["title_translations"]
    del record_video["description_translations"]
    record_video.commit()
    db.session.commit()

    with api_app.test_client() as client:
        # try get drupal
        file_frame = "http://cds.cern.ch/api/files/123/frame-1.jpg"
        with mock.patch(
            "cds.modules.records.api.CDSFileObject._link", return_value=file_frame
        ):
            res = client.get(url2, headers=drupal_headers)

        assert res.status_code == 200
        drupal = json.loads(res.data.decode("utf-8"))
        thumbnail = "http://cds.cern.ch/api/files/123/frame-1.jpg"
        expected = {
            "entries": [
                {
                    "entry": {
                        "caption_en": "in tempor reprehenderit enim "
                        "eiusmod <b><i>html</i></b>",
                        "caption_fr": "",
                        "copyright_date": "2017",
                        "copyright_holder": "CERN",
                        "creation_date": "2017-03-02",
                        "directors": "paperone, pluto",
                        "entry_date": "2017-09-25",
                        "id": "CERN-MOVIE-{0}-1-1".format(current_year),
                        "keywords": "keyword1, keyword2",
                        "license_body": "GPLv2",
                        "license_url": "http://license.cern.ch",
                        "producer": "nonna papera, zio paperino",
                        "record_id": "1",
                        "thumbnail": thumbnail,
                        "title_en": "My english title",
                        "title_fr": "",
                        "type": "360 video",
                        "video_length": "00:01:00",
                        "links": {
                            "240p": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                            "original": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                            "self": "http://localhost/record/1",
                            "thumbnail": "http://cds.cern.ch/api/files/123/frame-1.jpg",
                        },
                    }
                }
            ]
        }
        assert expected == drupal


def test_video_duration(app, video_published):
    """Validate calculated duration of video."""
    assert re.match(r"^\d\d:\d\d:\d\d$", video_published["duration"])


def test_videos_search(api_app, indexed_videos):
    """Test that searching for videos returns correct number of results."""
    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")
        # Get a query with only one record
        res = client.get(search_url, query_string={"q": "video"})
        assert_hits_len(res, 3)
        assert res.status_code == 200

        # Also make sure that there is no "Project" in the results
        res = client.get(search_url, query_string={"q": "Project"})
        assert_hits_len(res, 0)
        assert res.status_code == 200


def test_videos_search_tolerates_lucene_special_chars(api_app, indexed_videos):
    """Pasted titles with quotes/colons must not 400 (#1743 / #2025 Phase 1)."""
    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")
        for q in (
            'Prize: Steven',
            'light" :',
            '"for development',
            'Nobel Prize in Physics 1997 "for development of methods" : Steven Chu',
        ):
            res = client.get(search_url, query_string={"q": q})
            assert res.status_code == 200, q


def test_videos_search_improvement_examples(api_app, es, db):
    """Examples of queries that work after the search improvements (#2025)."""
    import copy

    from helpers import create_record

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "description": "Search improvements fixture",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
    }

    accented = copy.deepcopy(base)
    accented.update(
        {
            "title": {"title": "François CERN café"},
            "description": "Accent folding demo video",
            "doi": "10.1234/francois-cafe",
            "report_number": ["CERN-MOVIE-2024-42"],
            "legacy_recid": 991122,
            "translations": [
                {
                    "language": "en",
                    "title": {"title": "Only In Translation Higgs"},
                    "description": "translation-only string",
                }
            ],
        }
    )

    nobel = copy.deepcopy(base)
    nobel.update(
        {
            "title": {
                "title": (
                    'Nobel Prize in Physics 1997 "for development of methods" '
                    ": Steven Chu"
                )
            },
            "description": "Pasted title with quotes and colon",
            "report_number": ["CERN-MOVIE-1997-01"],
        }
    )

    phrase = copy.deepcopy(base)
    phrase.update(
        {
            "title": {"title": "the higgs boson discovery talk"},
            "description": "exact phrase ranking fixture",
            "report_number": ["CERN-MOVIE-2012-07"],
        }
    )

    created = [create_record(r) for r in (accented, nobel, phrase)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")

        # Accents match either way (François ↔ Francois, café ↔ cafe)
        res = client.get(search_url, query_string={"q": "Francois cafe"})
        assert_hits_len(res, 1)

        # DOI / legacy id / report number are findable
        res = client.get(search_url, query_string={"q": "10.1234/francois-cafe"})
        assert_hits_len(res, 1)
        res = client.get(search_url, query_string={"q": "991122"})
        assert_hits_len(res, 1)
        res = client.get(search_url, query_string={"q": "CERN-MOVIE-2024-42"})
        assert_hits_len(res, 1)

        # Translation-only string is searchable
        res = client.get(search_url, query_string={"q": "Only In Translation Higgs"})
        assert_hits_len(res, 1)

        # Pasted Nobel title with quotes/colon finds the record (not just 200)
        res = client.get(
            search_url,
            query_string={
                "q": (
                    'Nobel Prize in Physics 1997 "for development of methods" '
                    ": Steven Chu"
                )
            },
        )
        assert_hits_len(res, 1)

        # Known field filter still uses the strict path and scopes to title
        res = client.get(
            search_url, query_string={"q": 'title.title:"the higgs boson discovery"'}
        )
        assert_hits_len(res, 1)
        res = client.get(
            search_url, query_string={"q": 'title.title:"Accent folding demo"'}
        )
        assert_hits_len(res, 0)

        # Accents work the other way too (query with accents → ASCII title)
        res = client.get(search_url, query_string={"q": "François café"})
        assert_hits_len(res, 1)

        # Field filter still works with a space after the colon
        res = client.get(
            search_url, query_string={"q": 'title.title: "the higgs boson discovery"'}
        )
        assert_hits_len(res, 1)


def test_videos_search_keywords_contributors_and_description(api_app, es, db):
    """Keywords, contributors, and description-only text are searchable."""
    import copy

    from helpers import create_record

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "description": "generic fixture description",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
        "title": {"title": "Plain title without markers"},
        "report_number": ["CERN-MOVIE-KW-1"],
    }
    tagged = copy.deepcopy(base)
    tagged.update(
        {
            "title": {"title": "Keyword fixture video"},
            "description": "mentions antimatter nowhere else",
            "keywords": [{"name": "DarkMatterTag", "source": "CERN"}],
            "contributors": [
                {"name": "Curie, Marie", "role": "Speaker"},
                {"name": "Do, John", "role": "Camera Operator"},
            ],
            "report_number": ["CERN-MOVIE-KW-2"],
        }
    )
    other = copy.deepcopy(base)
    other["report_number"] = ["CERN-MOVIE-KW-3"]

    created = [create_record(r) for r in (tagged, other)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")

        res = client.get(search_url, query_string={"q": "DarkMatterTag"})
        assert_hits_len(res, 1)
        res = client.get(search_url, query_string={"q": "Curie"})
        assert_hits_len(res, 1)
        res = client.get(search_url, query_string={"q": "antimatter nowhere else"})
        assert_hits_len(res, 1)


def test_videos_search_report_number_is_exclusive(api_app, es, db):
    """Hyphenated report numbers must hit one record, not everything (#2025)."""
    import copy

    from helpers import create_record, get_json

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "description": "Report number exclusivity fixture",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
    }
    target = copy.deepcopy(base)
    target.update(
        {
            "title": {"title": "Report number target video"},
            "report_number": ["CERN-VIDEO-1997-001"],
        }
    )
    decoy = copy.deepcopy(base)
    decoy.update(
        {
            "title": {"title": "Report number decoy video"},
            "report_number": ["CERN-VIDEO-2012-099"],
            "description": "Mentions CERN and VIDEO and 1997 elsewhere",
        }
    )

    created = [create_record(r) for r in (target, decoy)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")
        res = client.get(search_url, query_string={"q": "CERN-VIDEO-1997-001"})
        assert_hits_len(res, 1)
        hit = get_json(res)["hits"]["hits"][0]["metadata"]
        assert hit["report_number"] == ["CERN-VIDEO-1997-001"]


def test_videos_search_phrase_ranks_title_above_scattered(api_app, es, db):
    """Exact title phrases rank above the same words scattered in description."""
    import copy

    from helpers import create_record, get_json

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
    }
    exact = copy.deepcopy(base)
    exact.update(
        {
            "title": {"title": "quantum chromodynamics primer"},
            "description": "unrelated abstract text",
            "report_number": ["CERN-MOVIE-PHRASE-1"],
        }
    )
    scattered = copy.deepcopy(base)
    scattered.update(
        {
            "title": {"title": "Something else entirely"},
            "description": "primer notes about chromodynamics in quantum labs",
            "report_number": ["CERN-MOVIE-PHRASE-2"],
        }
    )

    created = [create_record(r) for r in (exact, scattered)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")
        res = client.get(
            search_url, query_string={"q": "quantum chromodynamics primer"}
        )
        assert res.status_code == 200
        hits = get_json(res)["hits"]["hits"]
        assert len(hits) >= 2
        assert hits[0]["metadata"]["title"]["title"] == "quantum chromodynamics primer"


def test_videos_search_hides_restricted(api_app, es, db):
    """Restricted videos stay out of anonymous search results."""
    import copy

    from helpers import create_record, get_json

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "description": "Access filter search fixture",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
    }
    public = copy.deepcopy(base)
    public.update(
        {
            "title": {"title": "Public Access Zeta"},
            "report_number": ["CERN-MOVIE-ACCESS-1"],
        }
    )
    restricted = copy.deepcopy(base)
    restricted.update(
        {
            "title": {"title": "Secret Access Zeta"},
            "report_number": ["CERN-MOVIE-ACCESS-2"],
            "_access": {"read": ["search-secret-group"]},
        }
    )

    created = [create_record(r) for r in (public, restricted)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    with api_app.test_client() as client:
        search_url = url_for("invenio_records_rest.recid_list")
        res = client.get(search_url, query_string={"q": "Access Zeta"})
        assert_hits_len(res, 1)
        assert get_json(res)["hits"]["hits"][0]["metadata"]["title"]["title"] == (
            "Public Access Zeta"
        )


def test_videos_title_suggest(api_app, indexed_videos, json_headers):
    """Title suggest uses filtered search on /records/_suggest."""
    with api_app.test_client() as client:
        url = url_for("cds_records.records_title_suggest")
        res = client.get(
            url,
            headers=json_headers,
            query_string={"suggest-title": "vid", "size": 10},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "suggest-title" in data
        options = data["suggest-title"][0]["options"]
        assert options
        assert any("Video" in (o.get("text") or "") for o in options)


def test_videos_title_suggest_respects_access(api_app, es, db, users, json_headers):
    """Restricted titles stay out of suggest unless the user can see them."""
    import copy

    from flask_principal import RoleNeed, identity_loaded
    from helpers import create_record

    base = {
        "date": "2017-01-16",
        "duration": "00:01:00",
        "description": "Suggest access fixture",
        "publication_date": "2017-03-09",
        "$schema": "https://cds.cern.ch/schemas/records/videos/video/video-v1.0.0.json",
        "type": "Type",
        "category": "Category",
        "contributors": [{"name": "Do, John", "role": "Camera Operator"}],
        "copyright": {"holder": "CERN", "year": "2017"},
        "license": [{"license": "CERN"}],
        "language": "en",
    }
    public = copy.deepcopy(base)
    public["title"] = {"title": "Public Suggest Alpha"}
    public["report_number"] = ["CERN-MOVIE-SUGGEST-1"]
    restricted = copy.deepcopy(base)
    restricted["title"] = {"title": "Secret Suggest Alpha"}
    restricted["report_number"] = ["CERN-MOVIE-SUGGEST-2"]
    restricted["_access"] = {"read": ["suggest-secret-group"]}

    created = [create_record(r) for r in (public, restricted)]
    db.session.commit()
    RecordIndexer().bulk_index([record.id for _, record in created])
    RecordIndexer().process_bulk_queue()
    current_search_client.indices.refresh()

    url = url_for("cds_records.records_title_suggest")
    with api_app.test_client() as client:
        res = client.get(
            url, headers=json_headers, query_string={"suggest-title": "Suggest Alpha"}
        )
        assert res.status_code == 200
        titles = [o["text"] for o in res.get_json()["suggest-title"][0]["options"]]
        assert "Public Suggest Alpha" in titles
        assert "Secret Suggest Alpha" not in titles

    @identity_loaded.connect
    def _grant_secret_group(sender, identity):
        identity.provides.add(RoleNeed("suggest-secret-group"))

    with api_app.test_client() as client:
        login_user(db.session.get(User, users[0]))
        res = client.get(
            url, headers=json_headers, query_string={"suggest-title": "Suggest Alpha"}
        )
        assert res.status_code == 200
        titles = [o["text"] for o in res.get_json()["suggest-title"][0]["options"]]
        assert "Public Suggest Alpha" in titles
        assert "Secret Suggest Alpha" in titles


def test_serialize_record(app, api_app, users, api_project_published, json_headers):
    """Test the record embedded in the record page, as the API returns it."""
    (project, video_1, _) = api_project_published
    db.session.commit()

    for deposit in (project, video_1):
        pid, record = deposit.fetch_published()
        with app.test_request_context():
            login_user(db.session.get(User, users[0]))
            embedded = json.loads(json.dumps(serialize_record(pid, record)))

        with api_app.test_client() as client:
            login_user(db.session.get(User, users[0]))
            res = client.get(
                url_for("invenio_records_rest.recid_item", pid_value=pid.pid_value),
                headers=json_headers,
            )
            assert res.status_code == 200
            expected = json.loads(res.data.decode("utf-8"))
        # Each application context has its own session (Flask-SQLAlchemy 3):
        # release the user row updated by the login
        db.session.commit()

        assert sorted(embedded) == sorted(expected)
        for key in expected:
            if key != "links":
                assert embedded[key] == expected[key]
        # The API links of the UI application go through the ``/api`` mount
        links = embedded["links"]
        assert sorted(links) == sorted(expected["links"])
        assert links["self"] == "http://localhost/api/record/{0}".format(pid.pid_value)

    # The owner of the video gets the link to the form of its project
    assert links["project_edit"] == expected["links"]["project_edit"]
    assert links["project_edit"].endswith(
        "/deposit/project/{0}".format(project["_deposit"]["id"])
    )

    # Nothing is embedded for users who can not read the record
    pid, record = video_1.fetch_published()
    record["_access"] = {"read": [db.session.get(User, users[0]).email]}
    record.commit()
    db.session.commit()
    pid, record = video_1.fetch_published()
    with app.test_request_context():
        login_user(db.session.get(User, users[1]))
        assert serialize_record(pid, record) is None
    with app.test_request_context():
        login_user(db.session.get(User, users[2]))
        assert serialize_record(pid, record) is not None


def test_parse_video_chapters_html():
    """Chapters are found in the HTML of both description editors."""
    from cds.modules.records.utils import parse_video_chapters

    expected = [("00:00", "Intro"), ("01:30", "Results"), ("02:15", "Summary")]
    descriptions = [
        # HugeRTE: no newline after <br>, the first chapter right after <p>
        "<p><strong>Talk</strong></p>\n<p>00:00 Intro<br>01:30 Results<br>"
        "02:15 <em>Summary</em><br><br></p>",
        # CKEditor 4
        "Talk<br />\n00:00 Intro<br />\n01:30 Results<br />\n02:15 Summary",
        # Plain text
        "Talk\n00:00 Intro\n01:30 Results\n02:15 Summary",
    ]
    for description in descriptions:
        chapters = parse_video_chapters(description)
        assert [(c["timestamp"], c["title"]) for c in chapters] == expected
    # A time inside a sentence is not a chapter
    assert parse_video_chapters("<p>Coffee will be served at 10:30</p>") == []
