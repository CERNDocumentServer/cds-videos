# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015 2016 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile
from os.path import dirname, join
from time import sleep

import mock
import pytest
from cds.factory import create_app
from elasticsearch import RequestError
from flask_cli import ScriptInfo
from jsonresolver import JSONResolver
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonresolver.contrib.jsonschema import ref_resolver_factory
from cds.modules.deposit.api import Project, Video, video_resolver
from flask_security import login_user
from invenio_db import db as db_
from invenio_files_rest.models import Location, Bucket
from invenio_files_rest.views import blueprint as files_rest_blueprint
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_search import InvenioSearch, current_search, current_search_client
from sqlalchemy_utils.functions import create_database, database_exists


@pytest.yield_fixture(scope='session', autouse=True)
def app():
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()

    os.environ.update(
        APP_INSTANCE_PATH=os.environ.get(
            'INSTANCE_PATH', instance_path),
    )

    app = create_app(
        DEBUG_TB_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite://'),
        TESTING=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND="cache",
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        JSONSCHEMAS_HOST='cdslabs.cern.ch',
    )
    app.register_blueprint(files_rest_blueprint)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)


@pytest.yield_fixture()
def db(app):
    """Setup database."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.yield_fixture()
def location(db):
    """File system location."""
    tmppath = tempfile.mkdtemp()

    loc = Location(
        name='testloc',
        uri=tmppath,
        default=True
    )
    db.session.add(loc)
    db.session.commit()

    yield loc

    shutil.rmtree(tmppath)


@pytest.fixture()
def bucket(db, location):
    """Provide test bucket."""
    bucket = Bucket.create(location)
    db.session.commit()
    return bucket


@pytest.yield_fixture()
def es(app):
    """Provide elasticsearch access."""
    InvenioSearch(app)
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete())
        list(current_search.create())
    current_search_client.indices.refresh()
    yield current_search_client
    list(current_search.delete(ignore=[404]))


@pytest.fixture()
def datadir():
    """Get data directory."""
    return join(dirname(__file__), '..', 'data')


@pytest.fixture
def script_info(app):
    """Get ScriptInfo object for testing CLI."""
    return ScriptInfo(create_app=lambda info: app)


@pytest.fixture()
def video_mp4(datadir):
    """Get test video file."""
    return join(datadir, 'test.mp4')


@pytest.fixture()
def video_mov(datadir):
    """Get test video file."""
    return join(datadir, 'test.mov')


@pytest.fixture()
def online_video():
    """Get online test video file."""
    return 'http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4'


@pytest.fixture()
def users(app, db):
    """Create users."""
    with db.session.begin_nested():
        datastore = app.extensions['security'].datastore
        user1 = datastore.create_user(email='info@inveniosoftware.org',
                                      password='tester', active=True)
        user2 = datastore.create_user(email='test@inveniosoftware.org',
                                      password='tester2', active=True)
    db.session.commit()
    return [user1, user2]


@pytest.fixture()
def cds_jsonresolver(app):
    """Configure a jsonresolver for cds-dojson."""
    resolver = JSONResolver(plugins=['demo.json_resolver'])
    app.extensions['invenio-records'].ref_resolver_cls = ref_resolver_factory(
        resolver)
    app.extensions['invenio-records'].loader_cls = json_loader_factory(
        resolver)


@pytest.fixture()
def project(app, es, cds_jsonresolver, users, location, db):
    """New project with videos."""
    project_data = {
        'title': {
            'title': 'my project',
        },
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/project-v1.0.0.json'),
        '_access': {'read': 'open'},
        'videos': [],
    }
    project_video_1 = {
        'title': {
            'title': 'video 1',
        },
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/video-v1.0.0.json'),
        '_access': {'read': 'open'},
    }
    project_video_2 = {
        'title': {
            'title': 'video 2',
        },
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/video-v1.0.0.json'),
        '_access': {'read': 'open'},
    }
    with app.test_request_context():
        login_user(users[0])

        # create empty project
        project = Project.create(project_data).commit()

        # create videos
        video_1 = Video.create(project_video_1)
        video_2 = Video.create(project_video_2)

        # add videos inside the project
        video_1.project = project
        video_2.project = project

        # save project and video
        project.commit()
        video_1.commit()
        video_2.commit()

    db.session.commit()
    sleep(2)
    return (project, video_1, video_2)


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.fixture()
def project_published(app, project):
    """New published project with videos."""
    (project, video_1, video_2) = project
    with app.test_request_context():
        new_project = project.publish()
        new_videos = video_resolver(new_project.video_ids)
        assert len(new_videos) == 2
    return new_project, new_videos[0], new_videos[1]
