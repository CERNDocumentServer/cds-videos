# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016, 2017 CERN.
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
import random
import shutil
import tempfile
import uuid

from os.path import dirname, join

import requests
import mock
import pytest
from cds.factory import create_app
from cds.modules.deposit.api import Project
from cds.modules.webhooks.receivers import CeleryAsyncReceiver
from celery import chain
from celery import group
from celery import shared_task
from celery.messaging import establish_connection
from elasticsearch import RequestError
from flask.cli import ScriptInfo
from invenio_sequencegenerator.api import Template
from cds.modules.deposit.api import video_resolver
from flask_security import login_user
from invenio_access.models import ActionRoles, ActionUsers
from invenio_accounts.models import Role, User
from invenio_db import db as db_
from invenio_deposit import InvenioDepositREST
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
from invenio_pidstore.models import PersistentIdentifier
from uuid import uuid4

from helpers import create_category, sse_simple_add, sse_failing_task, \
    sse_success_task, new_project, prepare_videos_for_publish


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
        # Give a superuser role to admin
        superuser_role = Role(name='superuser')
        db.session.add(ActionRoles(
            action='superuser-access', role=superuser_role))
        datastore.add_role_to_user(admin, superuser_role)
    db.session.commit()
    id_1 = user1.id
    id_2 = user2.id
    id_3 = admin.id
    return [id_1, id_2, id_3]


@pytest.fixture()
def u_email(db, users):
    """Valid user email."""
    user = User.query.get(users[0])
    return user.email


@pytest.fixture()
def cds_depid(api_app, users, db, bucket, deposit_metadata):
    """New deposit with files."""
    record = {'title': {'title': 'fuu'}}
    record.update(deposit_metadata)
    with api_app.test_request_context():
        login_user(User.query.get(users[0]))
        deposit = Project.create(record)
        deposit['_deposit']['owners'].append('test-egroup@cern.ch')
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


@pytest.fixture(params=["mp4", "mov"])
def video(request, datadir):
    """Get test video file."""
    return join(datadir, 'test.{}'.format(request.param))


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


@pytest.yield_fixture()
def api_cds_jsonresolver_required_fields(api_app):
    """Configure a jsonresolver for cds-dojson."""
    resolver = JSONResolver(plugins=['demo.json_resolver_required_fields'])
    backup_ref = api_app.extensions['invenio-records'].ref_resolver_cls
    backup_json = api_app.extensions['invenio-records'].loader_cls
    api_app.extensions[
        'invenio-records'].ref_resolver_cls = ref_resolver_factory(
        resolver)
    api_app.extensions['invenio-records'].loader_cls = json_loader_factory(
        resolver)
    yield api_app
    api_app.extensions['invenio-records'].loader_cls = backup_json
    api_app.extensions['invenio-records'].ref_resolver_cls = backup_ref


@pytest.fixture()
def deposit_metadata():
    """General deposit metadata."""
    return {
        'date': '2016-12-03T00:00:00Z',
        'category': 'CERN',
        'type': 'MOVIE',
    }


@pytest.fixture()
def project_deposit_metadata(deposit_metadata):
    """Project deposit metadata."""
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
def video_deposit_metadata(deposit_metadata):
    """Video deposit metadata."""
    metadata = dict(
        title=dict(title='test video',),
        description=dict(value='in tempor reprehenderit enim eiusmod',),
        featured=True,
    )
    metadata.update(deposit_metadata)
    return metadata


@pytest.fixture()
def video_record_metadata():
    """Video record metadata."""
    metadata = {
        '_buckets': {'deposit': '14113947-0b79-40a3-b39d-3b118a6ae04c'},
        '_deposit': {
            'created_by': 1,
            'pid': {'value': 1},
            'extracted_metadata': {
                'bit_rate': '679886',
                'duration': '60.140000',
                'size': '5111048',
                'avg_frame_rate': '288000/12019',
                'codec_name': 'h264',
                'width': 640,
                'height': 360,
                'nb_frames': '1440',
                'display_aspect_ratio': '16:9',
                'color_range': 'tv',
                'tags': {
                    'compatible_brands': 'qt  ',
                    'creation_time': '1970-01-01T00:00:00.000000Z',
                    'encoder': 'Lavf52.93.0',
                    'major_brand': 'qt  ',
                    'minor_version': '512',
                },
            },
            'id': '0c547fefc0664ac9837d6a53a4890730',
            'owners': [1],
            'state': {'file_transcode': 'FAILURE',
                      'file_video_extract_frames': 'SUCCESS',
                      'file_video_metadata_extraction': 'SUCCESS'},
            'status': 'draft'
        },
        '_files': [
            dict(
                context_type='master',
                media_type='video',
                content_type='mp4',
                checksum='md5:1beda6154605f65a922fdc488c987d83',
                completed=True,
                key='test.mp4',
                frame=[
                    dict(
                        bucket_id='0692a21c-6864-41cb-8424-b0f83eeb261b',
                        checksum='md5:7b4ba010ee4bd84074208f634fe3a672',
                        completed=True,
                        key='frame-{}.jpg'.format(i),
                        links=dict(
                            self=('/api/files/0692a21c-6864-41cb-8424-b0f83eeb'
                                  '261b/frame-{}.jpg?versionId=7cc97a14-61f3-4'
                                  '902-a3cf-7a22af1859d8'.format(i))),
                        progress=100,
                        size=22774,
                        tags=dict(
                            master='f333e846-2620-416d-92e2-8137ed772692',
                            type='frame',
                            timestamp=(float(i) / 10) * 60.095
                        ),
                        version_id='7cc97a14-61f3-4902-a3cf-7a22af1859d8')
                    for i in range(11)
                ],
                tags=dict(
                    bit_rate='11915822',
                    width='4096',
                    height='2160',
                    uri_origin=(
                        'https://mediaarchive.cern.ch/MediaArchive/'
                        'Video/Public/Movies/CERN/2016/CERN-MOVIE-2016-06'
                        '6/CERN-MOVIE-2016-066-001/CERN-MOVIE-2016-066-00'
                        '1-11872-kbps-4096x2160-audio-128-kbps-stereo.mp4'),
                    duration='60.095',),
                subformat=[
                    dict(
                        context_type='subformat',
                        media_type='video',
                        content_type='mp4',
                        checksum='md5:{:032d}'.format(random.randint(1, 1000)),
                        completed=True,
                        key='CERN-MOVIE-2106-test[{}p]'.format(quality),
                        links=dict(
                            self='/api/files/...'),
                        progress=100,
                        size=4457627,
                        tags=dict(
                            _sorenson_job_id=str(uuid.uuid4()),
                            master=str(uuid.uuid4()),
                            preset_quality='{}p'.format(quality),),
                        version_id=str(uuid.uuid4()),)
                    for quality in enumerate([240, 360, 480, 720])
                ],
                playlist=[
                    dict(
                        context_type='playlist',
                        media_type='text',
                        content_type='smil',
                        checksum='md5:{:032d}'.format(random.randint(1, 1000)),
                        completed=True,
                        key='test.smil',
                        links=dict(
                            self='/api/files/...'),
                        progress=100,
                        size=12355,
                        tags=dict(
                            master=str(uuid.uuid4())),
                        version_id=str(uuid.uuid4()),)
                ],
            )
        ],
        'contributors': [
            {'name': 'paperone', 'role': 'Director'},
            {'name': 'topolino', 'role': 'Music by'},
            {'name': 'nonna papera', 'role': 'Producer'},
            {'name': 'pluto', 'role': 'Director'},
            {'name': 'zio paperino', 'role': 'Producer'}
        ],
        'copyright': {'url': 'www.copy.right'},
        "license": [{
            "license": "GPLv2",
            "url": "http://license.cern.ch",
        }],
        "title": {
            "title": "My english title"
        },
        "keywords": [
            {
                "source": "source1",
                "value": "keyword1",
            },
            {
                "source": "source2",
                "value": "keyword2",
            }
        ],
        "copyright": {
            "holder": "CERN",
            "url": "http://cern.ch",
            "year": "2017"
        },
        'title_translations': [
            {
                'language': 'fr',
                'title': 'My french title',
            }
        ],
        'description': {
            'value': 'in tempor reprehenderit enim eiusmod',
        },
        'description_translations': [
            {
                'language': 'fr',
                'value': 'france caption',
            }
        ],
        'language': 'en',
        'publication_date': '2017-03-02',
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
    """SMIL headers."""
    return [('Content-Type', 'application/smil'),
            ('Accept', 'application/smil')]


@pytest.fixture()
def drupal_headers(app):
    """SMIL headers."""
    return [('Content-Type', 'x-application/drupal'),
            ('Accept', 'x-application/drupal')]


@pytest.fixture()
def vtt_headers(app):
    """VTT headers."""
    return [('Content-Type', 'text/vtt'),
            ('Accept', 'text/vtt')]


@pytest.fixture()
def datacite_headers(app):
    """Datacite headers."""
    return [('Content-Type', 'application/x-datacite+xml'),
            ('Accept', 'application/x-datacite+xml')]


@pytest.fixture()
def project(app, deposit_rest, es, cds_jsonresolver, users, location, db,
            deposit_metadata):
    """New project with videos."""
    return new_project(app, deposit_rest, es, cds_jsonresolver, users,
                       location, db, deposit_metadata)


@pytest.fixture()
def api_project(api_app, deposit_rest, es, cds_jsonresolver, users, location,
                db, deposit_metadata):
    """New project with videos."""
    return new_project(api_app, deposit_rest, es, cds_jsonresolver, users,
                       location, db, deposit_metadata)


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.fixture()
def project_published(app, project):
    """New published project with videos."""
    (project, video_1, video_2) = project
    with app.test_request_context():
        prepare_videos_for_publish(video_1, video_2)
        new_project = project.publish()
        new_videos = video_resolver(new_project.video_ids)
        assert len(new_videos) == 2
    return new_project, new_videos[0], new_videos[1]


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.fixture()
def api_project_published(api_app, api_project):
    """New published project with videos."""
    (project, video_1, video_2) = api_project
    with api_app.test_request_context():
        prepare_videos_for_publish(video_1, video_2)
        new_project = project.publish()
        new_videos = video_resolver(new_project.video_ids)
        assert len(new_videos) == 2
    return new_project, new_videos[0], new_videos[1]


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.fixture()
def video_published(app, project_published):
    """New published project with videos."""
    return project_published[1]


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
            result = workflow.apply_async()
            self._serialize_result(event=event, result=result)
            self.persist(event=event, result=result)

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


@pytest.fixture()
def recid_pid():
    """PID for minimal record."""
    return PersistentIdentifier(
        pid_type='recid', pid_value='123', status='R', object_type='rec',
        object_uuid=uuid4())
