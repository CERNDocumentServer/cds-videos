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

import requests
import mock
import pytest
from cds.factory import create_app
from cds.modules.deposit.api import CDSDeposit
from cds.modules.webhooks.receivers import CeleryAsyncReceiver
from celery import chain
from celery import group
from celery import shared_task
from celery.messaging import establish_connection
from elasticsearch import RequestError
from flask.cli import ScriptInfo
from invenio_sequencegenerator.api import Template
from cds.modules.deposit.api import Project, Video, video_resolver
from flask_security import login_user
from invenio_access.models import ActionUsers
from invenio_accounts.models import User
from invenio_db import db as db_
from invenio_deposit import InvenioDepositREST
from invenio_deposit.api import Deposit
from invenio_files_rest.models import Location, Bucket
from invenio_files_rest.views import blueprint as files_rest_blueprint
from invenio_indexer import InvenioIndexer
from invenio_oauth2server.models import Token
from invenio_pidstore import InvenioPIDStore
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_previewer import InvenioPreviewer
from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.utils import PIDConverter
from invenio_search import InvenioSearch, current_search, current_search_client
from invenio_webhooks import InvenioWebhooks
from invenio_webhooks import current_webhooks
from invenio_webhooks.models import CeleryReceiver
from jsonresolver import JSONResolver
from jsonresolver.contrib.jsonref import json_loader_factory
from jsonresolver.contrib.jsonschema import ref_resolver_factory
from six import BytesIO
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy_utils.functions import create_database, database_exists
from invenio_files_rest.models import ObjectVersion

from helpers import create_category, sse_simple_add, sse_failing_task, \
    sse_success_task


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
            'SQLALCHEMY_DATABASE_URI',
            'postgresql+psycopg2://localhost/cds_testing'),
        #  SQLALCHEMY_ECHO=True,
        TESTING=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND='cache',
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_TRACK_STARTED=True,
        BROKER_TRANSPORT='redis',
        JSONSCHEMAS_HOST='cdslabs.cern.ch',
        DEPOSIT_UI_ENDPOINT='{scheme}://{host}/deposit/{pid_value}',

    )
    app.register_blueprint(files_rest_blueprint)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)


@pytest.yield_fixture(scope='session')
def celery_not_fail_on_eager_app(app):
    """Celery configuration that does not raise errors inside test."""
    instance_path = tempfile.mkdtemp()

    os.environ.update(
        APP_INSTANCE_PATH=os.environ.get(
            'INSTANCE_PATH', instance_path),
    )

    app = create_app(
        DEBUG_TB_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI',
            'postgresql+psycopg2://localhost/cds_testing'),
        TESTING=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND='cache',
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=False,
        CELERY_TRACK_STARTED=True,
        BROKER_TRANSPORT='redis',
        JSONSCHEMAS_HOST='cdslabs.cern.ch',
        PREVIEWER_PREFERENCE=['cds_video', ],
        RECORDS_UI_ENDPOINTS=dict(
            video_preview=dict(
                pid_type='depid',
                route='/deposit/<pid_value>/preview/video/<filename>',
                view_imp='cds.modules.previewer.views.preview_depid',
                record_class='cds.modules.deposit.api:Video',
            ),
        )

    )
    app.register_blueprint(files_rest_blueprint)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)


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
    id_1 = user1.id
    id_2 = user2.id
    return [id_1, id_2]


@pytest.fixture()
def u_email(db, users):
    """Valid user email."""
    user = User.query.get(users[0])
    return user.email


@pytest.fixture()
def depid(app, users, db):
    """New deposit with files."""
    record = {
        'title': {'title': 'fuu'}
    }
    with app.test_request_context():
        login_user(User.query.get(users[0]))
        deposit = Deposit.create(record)
        deposit.commit()
        db.session.commit()
    return deposit['_deposit']['id']


@pytest.fixture()
def cds_depid(api_app, users, db, bucket, deposit_metadata):
    """New deposit with files."""
    record = {'title': {'title': 'fuu'}}
    record.update(deposit_metadata)
    with api_app.test_request_context():
        login_user(User.query.get(users[0]))
        deposit = CDSDeposit.create(record)
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
    queue = app.config['INDEXER_MQ_QUEUE']
    with establish_connection() as c:
        q = queue(c)
        q.declare()
    yield current_search_client
    list(current_search.delete(ignore=[404]))


@pytest.fixture()
def pidstore(app):
    """Initialize invenio-indexer app."""
    return InvenioPIDStore(app)


@pytest.fixture()
def indexer(app):
    """Initialize invenio-indexer app."""
    return InvenioIndexer(app)


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
def webhooks(app):
    """Init webhooks API."""
    if 'invenio-webhooks' not in app.extensions:
        InvenioWebhooks(app)
    return app


@pytest.fixture()
def previewer_app(app):
    """Init deposit REST API."""
    if 'invenio-previewer' not in app.extensions:
        InvenioPreviewer(app)
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
def cds_jsonresolver_required_fields(app):
    """Configure a jsonresolver for cds-dojson."""
    resolver = JSONResolver(plugins=['demo.json_resolver_required_fields'])
    app.extensions['invenio-records'].ref_resolver_cls = ref_resolver_factory(
        resolver)
    app.extensions['invenio-records'].loader_cls = json_loader_factory(
        resolver)


@pytest.fixture()
def deposit_metadata():
    """Deposit metadata."""
    return {
        'date': '2016-12-03T00:00:00Z',
        'category': 'CERN',
        'type': 'MOVIE',
    }


@pytest.fixture()
def project_metadata(deposit_metadata):
    """Simple project metadata."""
    metadata = {
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
    metadata.update(deposit_metadata)
    return metadata


@pytest.fixture()
def video_metadata():
    """Deposit metadata."""
    metadata = {
        "_files": [
            {
                "tags": {
                    "bit_rate": "11915822",
                    "height": "2160",
                    "uri_origin": (
                        "https://mediaarchive.cern.ch/MediaArchive/"
                        "Video/Public/Movies/CERN/2016/CERN-MOVIE-2016-06"
                        "6/CERN-MOVIE-2016-066-001/CERN-MOVIE-2016-066-00"
                        "1-11872-kbps-4096x2160-audio-128-kbps-stereo.mp4"
                    ),
                    "width": "4096"
                },
                "video": [
                    {
                        "checksum": "md5:127efd1d7b090924d6c2e46848987b69",
                        "completed": True,
                        "key": (
                            "CERN-MOVIE-2016-066-001-11872-kbps-"
                            "4096x2160-audio-128-kbps-stereo[240p].mp4"
                        ),
                        "links": {
                            "self": (
                                "/api/files/d2692fc0-a49d-40b9-824f-42099c"
                                "b98fd3/CERN-MOVIE-2016-066-001-11872-kbps"
                                "-4096x2160-audio-128-kbps-stereo[240p].mp"
                                "4?versionId=02ff769e-21e0-4a79-93b1-7e82a"
                                "9e8efe1"
                            ),
                        },
                        "progress": 100,
                        "size": 4457627,
                        "tags": {
                            "_sorenson_job_id":
                                "1d0ab2fa-e26b-41c1-8fca-45afe2d00b61",
                            "master":
                                "9e4ce306-077c-463c-8a0e-b368edcdd7c3",
                            "preset_quality": "240p",
                            "type": "video"
                        },
                        "version_id":
                            "02ff769e-21e0-4a79-93b1-7e82a9e8efe1"
                    },
                    {
                        "checksum": "",
                        "completed": True,
                        "key": (
                            "CERN-MOVIE-2016-066-001-11872-kbps-"
                            "4096x2160-audio-128-kbps-stereo[360p].mp4"
                        ),
                        "links": {
                            "self": (
                                "/api/files/d2692fc0-a49d-40b9-824f-42099c"
                                "b98fd3/CERN-MOVIE-2016-066-001-11872-kbps"
                                "-4096x2160-audio-128-kbps-stereo[360p].mp"
                                "4?versionId=e5f98169-a041-47d0-ae24-f1734"
                                "44c1147"
                            ),
                        },
                        "progress": 100,
                        "size": 0,
                        "tags": {
                            "_sorenson_job_id":
                                "8d6f784c-f20f-45e6-a18c-bb1d186f46b0",
                            "master":
                                "9e4ce306-077c-463c-8a0e-b368edcdd7c3",
                            "preset_quality": "360p",
                            "type": "video"
                        },
                        "version_id":
                            "e5f98169-a041-47d0-ae24-f173444c1147"
                    },
                    {
                        "checksum": "md5:9999176fd09d9c54ecb56534fae0ff54",
                        "completed": True,
                        "key": (
                            "CERN-MOVIE-2016-066-001-11872-kbps-"
                            "4096x2160-audio-128-kbps-stereo[480p].mp4"
                        ),
                        "links": {
                            "self": (
                                "/api/files/d2692fc0-a49d-40b9-824f-42099c"
                                "b98fd3/CERN-MOVIE-2016-066-001-11872-kbps"
                                "-4096x2160-audio-128-kbps-stereo[480p].mp"
                                "4?versionId=92e6ac64-708a-4075-846a-6e385"
                                "3707a1a"
                            ),
                        },
                        "progress": 100,
                        "size": 14382281,
                        "tags": {
                            "_sorenson_job_id":
                                "deb59f6a-5836-4936-9d61-06516a045b03",
                            "master":
                                "9e4ce306-077c-463c-8a0e-b368edcdd7c3",
                            "preset_quality": "480p",
                            "type": "video"
                        },
                        "version_id":
                            "92e6ac64-708a-4075-846a-6e3853707a1a"
                    },
                    {
                        "checksum": "md5:fb3d75b05bce32cca582e69316a97918",
                        "completed": True,
                        "key": (
                            "CERN-MOVIE-2016-066-001-11872-kbps-"
                            "4096x2160-audio-128-kbps-stereo[720p].mp4"
                        ),
                        "links": {
                            "self": (
                                "/api/files/d2692fc0-a49d-40b9-824f-42099c"
                                "b98fd3/CERN-MOVIE-2016-066-001-11872-kbps"
                                "-4096x2160-audio-128-kbps-stereo[720p].mp"
                                "4?versionId=15d67ae2-f998-4681-9c26-6770a"
                                "c0e18c4"
                            ),
                        },
                        "progress": 100,
                        "size": 26662844,
                        "tags": {
                            "_sorenson_job_id":
                                "6c3d597e-3eed-43eb-b8d0-e773f767d853",
                            "master":
                                "9e4ce306-077c-463c-8a0e-b368edcdd7c3",
                            "preset_quality": "720p",
                            "type": "video"
                        },
                        "version_id":
                            "15d67ae2-f998-4681-9c26-6770ac0e18c4"
                    }
                ]
            }
        ],
    }
    return metadata


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
def smil_headers(app):
    """JSON headers."""
    return [('Content-Type', 'application/smil'),
            ('Accept', 'application/smil')]


@pytest.fixture()
def project(api_app, deposit_rest, es, cds_jsonresolver, users, location, db,
            deposit_metadata):
    """New project with videos."""
    project_data = {
        'title': {
            'title': 'my project',
        },
        'description': {
            'value': 'in tempor reprehenderit enim eiusmod',
        },
    }
    project_data.update(deposit_metadata)
    project_video_1 = {
        'title': {
            'title': 'video 1',
        },
        'description': {
            'value': 'in tempor reprehenderit enim eiusmod',
        },
    }
    project_video_1.update(deposit_metadata)
    project_video_2 = {
        'title': {
            'title': 'video 2',
        },
        'description': {
            'value': 'in tempor reprehenderit enim eiusmod',
        },
    }
    project_video_2.update(deposit_metadata)
    with api_app.test_request_context():
        login_user(User.query.get(users[0]))

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
def project_published(api_app, project):
    """New published project with videos."""
    (project, video_1, video_2) = project
    with api_app.test_request_context():
        new_project = project.publish()
        new_videos = video_resolver(new_project.video_ids)
        assert len(new_videos) == 2
    return new_project, new_videos[0], new_videos[1]


@pytest.fixture()
def mock_sorenson():
    """Mock requests to the Sorenson server."""
    def mocked_encoding(input_file, output_file, preset_name, aspect_ratio):
        shutil.copyfile(input_file, output_file)  # just copy file
        return '1234'
    mock.patch(
        'cds.modules.webhooks.tasks.start_encoding'
    ).start().side_effect = mocked_encoding

    mock.patch(
        'cds.modules.webhooks.tasks.get_encoding_status'
    ).start().side_effect = [
        ('Waiting', 0),
        ('Transcoding', 45),
        ('Transcoding', 95),
        ('Finished', 100),
    ] * 50  # repeat for multiple usages of the mocked method

    mock.patch(
        'cds.modules.webhooks.tasks.stop_encoding'
    ).start().return_value = None


@pytest.fixture
def access_token(api_app, db, users):
    """Fixture that create an access token."""
    with db.session.begin_nested():
        tester_id = User.query.get(users[0]).id
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


@pytest.fixture
def workflow_receiver(api_app, db, webhooks, es, cds_depid):
    """Workflow receiver."""
    class TestReceiver(CeleryAsyncReceiver):
        def run(self, event):
            workflow = chain(
                sse_simple_add().s(x=1, y=2, deposit_id=cds_depid),
                group(sse_failing_task().s(), sse_success_task().s())

            )
            event.payload['deposit_id'] = cds_depid
            with db.session.begin_nested():
                flag_modified(event, 'payload')
                db.session.expunge(event)
            db.session.commit()
            self.persist(
                event=event, result=workflow.apply_async())

        def _raw_info(self, event):
            result = self._deserialize_result(event)
            return (
                [{'add': result.parent}],
                [
                    {'failing': result.children[0]},
                    {'failing': result.children[1]}
                ]
            )

    receiver_id = 'add-receiver'
    from cds.celery import celery
    celery.flask_app.extensions['invenio-webhooks'].register(
        receiver_id, TestReceiver)
    current_webhooks.register(receiver_id, TestReceiver)
    return receiver_id


@pytest.fixture()
def category_1(api_app, es, indexer, pidstore, cds_jsonresolver):
    """Create a fixture for category."""
    data = {
        'name': 'open',
        'types': ['video', 'footage'],
        '_record_type': ['video', 'project'],
    }
    return create_category(api_app=api_app, db=db_, data=data)


@pytest.fixture()
def category_2(api_app, es, indexer, pidstore, cds_jsonresolver):
    """Create a fixture for category."""
    data = {
        'name': 'atlas',
        'types': ['video'],
        '_record_type': ['video'],
    }
    return create_category(api_app=api_app, db=db_, data=data)


@pytest.fixture(autouse=True)
def templates(app, db):
    """Register CDS templates for sequence generation."""
    Template.create(name='project-v1_0_0',
                    meta_template='{category}-{type}-{year}-{counter}',
                    start=1)
    Template.create(name='video-v1_0_0',
                    meta_template='{project-v1_0_0}-{counter}',
                    start=1)
    db.session.commit()


@pytest.fixture()
def local_file(db, bucket, location, online_video):
    """A local file."""
    response = requests.get(online_video, stream=True)
    object_version = ObjectVersion.create(
        bucket, "test.mp4", stream=response.raw)
    version_id = object_version.version_id
    db.session.commit()
    return version_id
