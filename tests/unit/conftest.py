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

import pytest
from flask_cli import FlaskCLI, ScriptInfo
from invenio_db import db as db_
from invenio_files_rest.models import Location
from invenio_files_rest.views import blueprint as files_rest_blueprint
from sqlalchemy_utils.functions import create_database, database_exists

from cds.factory import create_app


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
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True
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


@pytest.yield_fixture()
def es(app):
    """Provide elasticsearch access."""
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
