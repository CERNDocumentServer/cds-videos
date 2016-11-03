# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016 CERN.
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
from celery import shared_task
from elasticsearch import RequestError
from flask.cli import ScriptInfo
from invenio_oauth2server.models import Token
from invenio_webhooks import current_webhooks
from invenio_webhooks.models import CeleryReceiver
from jsonresolver import JSONResolver
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonresolver.contrib.jsonschema import ref_resolver_factory
from cds.modules.deposit.api import Project, Video, video_resolver
from flask_security import login_user
from invenio_access.models import ActionUsers
from invenio_db import db as db_
from invenio_deposit.api import Deposit
from invenio_files_rest.models import Location, Bucket
from invenio_files_rest.views import blueprint as files_rest_blueprint
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_search import InvenioSearch, current_search, current_search_client
from sqlalchemy_utils.functions import create_database, database_exists
from invenio_deposit import InvenioDepositREST
from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.utils import PIDConverter
from six import BytesIO


@pytest.yield_fixture(scope='session', autouse=True)
def app():
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    sorenson_output = tempfile.mkdtemp()

    os.environ.update(
        APP_INSTANCE_PATH=os.environ.get(
            'INSTANCE_PATH', instance_path),
    )

    app = create_app(
        DEBUG_TB_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite://'),
        # SQLALCHEMY_ECHO=True,
        TESTING=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND='cache',
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_TRACK_STARTED=True,
        BROKER_TRANSPORT='redis',
        JSONSCHEMAS_HOST='cdslabs.cern.ch',
        CDS_SORENSON_OUTPUT_FOLDER=sorenson_output,
    )
    app.register_blueprint(files_rest_blueprint)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)
    shutil.rmtree(sorenson_output)


@pytest.yield_fixture()
def api_app(app):
    """Flask API application fixture."""
    api_app = app.wsgi_app.mounts['/api']
    with api_app.app_context():
        yield api_app


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
def users(app, db):
    """Create users."""
    with db.session.begin_nested():
        datastore = app.extensions['security'].datastore
        user1 = datastore.create_user(email='info@inveniosoftware.org',
                                      password='tester', active=True)
        user2 = datastore.create_user(email='test@inveniosoftware.org',
                                      password='tester2', active=True)
        admin = datastore.create_user(email='admin@inveniosoftware.org',
                                      password='tester3', active=True)
        # Assign deposit-admin-access to admin only.
        db.session.add(ActionUsers(
            action='deposit-admin-access', user=admin
        ))
    db.session.commit()
    return [user1, user2]


@pytest.fixture()
def u_email(db, users):
    """Valid user email."""
    db.session.add(users[0])
    return users[0].email


@pytest.fixture()
def depid(app, users, db):
    """New deposit with files."""
    record = {
        'title': {'title': 'fuu'}
    }
    with app.test_request_context():
        login_user(users[0])
        deposit = Deposit.create(record)
        deposit.commit()
        db.session.commit()
    return deposit['_deposit']['id']


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
        list(current_search.delete(ignore=[404]))
        list(current_search.create(ignore=[400]))
    current_search_client.indices.refresh()
    yield current_search_client
    list(current_search.delete(ignore=[404]))


@pytest.fixture()
def records_rest_app(app):
    """Init deposit REST API."""
    if 'invenio-records-rest' not in app.extensions:
        InvenioRecordsREST(app)
    return app


@pytest.fixture()
def deposit_rest(app, records_rest_app):
    """Init deposit REST API."""
    if 'invenio-deposit-rest' not in app.extensions:
        InvenioDepositREST(app)
        app.url_map.converters['pid'] = PIDConverter
    return app


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
def cds_jsonresolver(app):
    """Configure a jsonresolver for cds-dojson."""
    resolver = JSONResolver(plugins=['demo.json_resolver'])
    app.extensions['invenio-records'].ref_resolver_cls = ref_resolver_factory(
        resolver)
    app.extensions['invenio-records'].loader_cls = json_loader_factory(
        resolver)


@pytest.fixture()
def project_metadata():
    """Simple project metadata."""
    return {
        'title': {
            'title': 'my project',
            'subtitle': 'tempor quis elit mollit',
        },
        'creator': {
            'email': 'test@cds.cern.ch',
            'contribution': 'Fuu Bar',
            'name': 'John Doe',
        },
        'description': {
            'value': 'in tempor reprehenderit enim eiusmod',
        },
        'contributors': [
            {
                'name': 'amet',
                'role': 'Editor'
            },
            {
                'name': 'in tempor reprehenderit enim eiusmod',
                'role': 'Camera operator',
                'email': '1bABAg03RaVG3@JTHWJUUBLgqpgfaagop.wsx',
            },
            {
                'name': 'adipisicing nulla ipsum voluptate',
                'role': 'Director'
            },
            {
                'name': 'commodo veniam dolore',
                'role': 'Editor'
            }
        ],
    }


@pytest.fixture()
def data_file_1():
    """Data for file 1."""
    filename = 'test.json'
    file_to_upload = (BytesIO(b'### Testing textfile ###'), filename)
    return {'file': file_to_upload, 'name': filename}


@pytest.fixture()
def data_file_2():
    """Data for file 2."""
    filename = 'test2.json'
    file_to_upload = (BytesIO(b'### Testing textfile 2 ###'), filename)
    return {'file': file_to_upload, 'name': filename}


@pytest.fixture()
def json_headers(app):
    """JSON headers."""
    return [('Content-Type', 'application/json'),
            ('Accept', 'application/json')]


@pytest.fixture()
def project(app, deposit_rest, es, cds_jsonresolver, users, location, db):
    """New project with videos."""
    project_data = {
        'title': {
            'title': 'my project',
        },
    }
    project_video_1 = {
        'title': {
            'title': 'video 1',
        },
    }
    project_video_2 = {
        'title': {
            'title': 'video 2',
        },
    }
    with app.test_request_context():
        login_user(users[0])

        # create empty project
        project = Project.create(project_data).commit()

        # create videos
        project_video_1['_project_id'] = project['_deposit']['id']
        project_video_2['_project_id'] = project['_deposit']['id']
        video_1 = Video.create(project_video_1)
        video_2 = Video.create(project_video_2)

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


@pytest.fixture()
def mock_sorenson():
    """Mock requests to the Sorenson server."""
    mock.patch(
        'cds.modules.webhooks.tasks.start_encoding'
    ).start().return_value = 123

    mock.patch(
        'cds.modules.webhooks.tasks.get_encoding_status'
    ).start().side_effect = [
        dict(Status=dict(Progress=0, TimeFinished=None)),
        dict(Status=dict(Progress=45, TimeFinished=None)),
        dict(Status=dict(Progress=95, TimeFinished=None)),
        dict(Status=dict(Progress=100, TimeFinished='12:00')),
    ] * 5  # repeat for multiple usages of the mocked method

    mock.patch(
        'cds.modules.webhooks.tasks.stop_encoding'
    ).start().return_value = None


@pytest.fixture
def access_token(app, db, users):
    """Fixture that create an access token."""
    db.session.add(users[0])
    tester_id = users[0].id
    with app.app_context():
        token = Token.create_personal(
            'test-personal-{0}'.format(tester_id),
            tester_id,
            scopes=['webhooks:event'],
            is_internal=True,
        ).access_token
        db.session.commit()
        return token


@shared_task()
def add(x, y):
    """Simple shared task."""
    return x + y


@pytest.fixture
def receiver(api_app):
    """Register test celery receiver."""
    class TestReceiver(CeleryReceiver):

        def run(self, event):
            ret = add.apply(kwargs=event.payload).get()
            event.response['message'] = ret

    current_webhooks.register('test-receiver', TestReceiver)
    return 'test-receiver'
