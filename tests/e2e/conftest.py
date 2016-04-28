# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""Pytest configuration.

Before running any of the tests you must have initialized the assets using
the ``script scripts/setup-assets.sh``.
"""

from __future__ import absolute_import, print_function

import os
import pkg_resources
import pytest
import shutil
import tempfile
import uuid

from cds_dojson.marc21 import marc21
from dojson.contrib.marc21.utils import create_record, split_blob
from elasticsearch.exceptions import RequestError
from invenio_db import db as _db
from invenio_indexer.api import RecordIndexer
from invenio_pidstore import current_pidstore
from invenio_records.api import Record
from invenio_search import current_search, current_search_client
from selenium import webdriver
from sqlalchemy_utils.functions import create_database, database_exists

from cds.factory import create_app


@pytest.yield_fixture(scope='session', autouse=True)
def base_app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()

    os.environ.update(
        APP_INSTANCE_PATH=instance_path
    )

    app = create_app(
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
        DEBUG_TB_ENABLED=False,
        SECRET_KEY="CHANGE_ME",
        SECURITY_PASSWORD_SALT="CHANGE_ME",
        MAIL_SUPPRESS_SEND=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        TESTING=True,
    )

    with app.app_context():
        yield app

    # Teardown
    shutil.rmtree(instance_path)


@pytest.yield_fixture(scope='session')
def db(base_app):
    """Initialize database."""
    # Init
    if not database_exists(str(_db.engine.url)):
        create_database(str(_db.engine.url))
    _db.create_all()

    yield _db

    # Teardown
    _db.session.remove()
    _db.drop_all()


@pytest.yield_fixture(scope='session')
def es(base_app):
    """Provide elasticsearch access."""
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete())
        list(current_search.create())
    current_search_client.indices.refresh()

    yield current_search_client

    list(current_search.delete(ignore=[404]))


@pytest.yield_fixture(scope='session', autouse=True)
def app(base_app, es, db):
    """Application with ES and DB."""
    yield base_app


def pytest_generate_tests(metafunc):
    """Override pytest's default test collection function.

    For each test in this directory which uses the `env_browser` fixture,
    the given test is called once for each value found in the
    `E2E_WEBDRIVER_BROWSERS` environment variable.
    """
    if 'env_browser' in metafunc.fixturenames:
        # In Python 2.7 the fallback kwarg of os.environ.get is `failobj`,
        # in 3.x it's `default`.
        browsers = os.environ.get('E2E_WEBDRIVER_BROWSERS',
                                  'Firefox').split()
        metafunc.parametrize('env_browser', browsers, indirect=True)


@pytest.yield_fixture()
def env_browser(request):
    """Fixture for a webdriver instance of the browser."""
    if request.param is None:
        request.param = "Firefox"

    # Create instance of webdriver.`request.param`()
    browser = getattr(webdriver, request.param)()

    yield browser

    # Quit the webdriver instance
    browser.quit()


@pytest.fixture()
def demo_records(app):
    """Create demo records."""
    data_path = pkg_resources.resource_filename(
        'cds.modules.fixtures', 'data/records.xml'
    )

    with open(data_path) as source:
        indexer = RecordIndexer()
        with _db.session.begin_nested():
            for index, data in enumerate(split_blob(source.read()), start=1):
                # create uuid
                rec_uuid = uuid.uuid4()
                # do translate
                record = marc21.do(create_record(data))
                # create PID
                current_pidstore.minters['recid'](
                    rec_uuid, record
                )
                # create record
                indexer.index(Record.create(record, id_=rec_uuid))
        _db.session.commit()
    return data_path
