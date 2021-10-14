# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016, 2017, 2019, 2020 CERN.
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

import json
import os
import shutil
import tempfile
from datetime import datetime
from os.path import dirname, join
from time import sleep
from uuid import uuid4

import jsonresolver
import mock
import pytest
import requests
from cds_sorenson.api import _get_quality_preset
from cds_sorenson.error import InvalidResolutionError
from celery import chain, group, shared_task
from celery.messaging import establish_connection
from elasticsearch import RequestError
from flask.cli import ScriptInfo
from flask_security import login_user
from invenio_access.models import ActionRoles
from invenio_access.permissions import superuser_access
from invenio_accounts.models import Role, User
from invenio_db import db as db_
from invenio_deposit.permissions import action_admin_access
from invenio_files_rest.models import Bucket, Location, ObjectVersion
from invenio_files_rest.views import blueprint as files_rest_blueprint
from invenio_indexer import InvenioIndexer
from invenio_indexer.api import RecordIndexer
from invenio_oauth2server.models import Token
from invenio_pidstore import InvenioPIDStore
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_previewer import InvenioPreviewer
from invenio_search import InvenioSearch, current_search, current_search_client
from invenio_sequencegenerator.api import Template
from six import BytesIO
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy_utils.functions import create_database, database_exists
from werkzeug.routing import Rule

from cds.factory import create_app
from cds.modules.deposit.api import Project, Video
from cds.modules.records.resolver import record_resolver
from cds.modules.redirector.views import api_blueprint as cds_api_blueprint
from helpers import (create_category, create_keyword, create_record,
                     endpoint_get_schema, new_project,
                     prepare_videos_for_publish, rand_md5, rand_version_id,
                     sse_failing_task, sse_simple_add, sse_success_task)


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
        TESTING=True,
        CELERY_ALWAYS_EAGER=True,
        CELERY_RESULT_BACKEND='cache',
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_TRACK_STARTED=True,
        JSONSCHEMAS_HOST='cdslabs.cern.ch',
        DEPOSIT_UI_ENDPOINT='{scheme}://{host}/deposit/{pid_value}',
        PIDSTORE_DATACITE_DOI_PREFIX='10.0000',
        # FIXME
        ACCOUNTS_JWT_ENABLE=False,
        THEOPLAYER_LICENCE_KEY='CHANGE_ME',
        PRESERVE_CONTEXT_ON_EXCEPTION=False
    )
    app.register_blueprint(files_rest_blueprint)
    app.register_blueprint(cds_api_blueprint)

    with app.app_context():
        yield app

    shutil.rmtree(instance_path)


@pytest.fixture()
def previewer_deposit(app):
    """."""
    # FIXME workaround for previewer tests because they require app and api_app
    from invenio_records_rest import InvenioRecordsREST
    from invenio_deposit import InvenioDepositREST
    from invenio_records_rest.utils import PIDConverter
    backup = app.debug
    app.debug = False
    if 'invenio-records-rest' not in app.extensions:
        InvenioRecordsREST(app)
    if 'invenio-deposit-rest' not in app.extensions:
        InvenioDepositREST(app)
        app.url_map.converters['pid'] = PIDConverter
    app.debug = backup
    return app


@pytest.yield_fixture()
def api_app(app):
    """Flask API application fixture."""
    api_app = app.wsgi_app.mounts['/api']
    #  with app.app_context():
    with api_app.test_request_context():
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
        name='videos',
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
        admin = datastore.create_user(
            email='admin@inveniosoftware.org',
            password='tester3', active=True)
        superadmin = datastore.create_user(
            email='superadmin@inveniosoftware.org',
            password='tester4', active=True)
        # Give a admin role to admin
        admin_role = Role(name='admin')
        db.session.add(ActionRoles(
            action=action_admin_access.value, role=admin_role))
        datastore.add_role_to_user(admin, admin_role)
        # Give a superadmin role to superadmin
        superadmin_role = Role(name='superadmin')
        db.session.add(ActionRoles(
            action=superuser_access.value, role=superadmin_role))
        datastore.add_role_to_user(superadmin, superadmin_role)
    db.session.commit()
    id_1 = user1.id
    id_2 = user2.id
    id_4 = admin.id
    return [id_1, id_2, id_4]


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
        deposit['_access'] = {'update': ['test-egroup@cern.ch']}
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
def previewer_app(app, previewer_deposit):
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


@pytest.fixture(params=['test.mp4', 'test.mov'])
def video(request, datadir):
    """Get test video file."""
    return join(datadir, request.param)


@pytest.fixture(params=['test.mp4', 'test_small.mp4', 'test.mov'])
def video_with_small(request, datadir):
    """Get test video file (including small one)."""
    return join(datadir, request.param)


@pytest.fixture()
def online_video():
    """Get online test video file."""
    return 'http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4'


@pytest.fixture()
def cds_jsonresolver(app):
    """Configure a jsonresolver for cds-dojson."""
    @jsonresolver.hookimpl
    def jsonresolver_loader(url_map):
        url_map.add(Rule(
            '/schemas/<path:path>', endpoint=endpoint_get_schema,
            host='cdslabs.cern.ch'
        ))


@pytest.fixture()
def api_cds_jsonresolver(api_app):
    """Configure a jsonresolver for cds-dojson."""
    @jsonresolver.hookimpl
    def jsonresolver_loader(url_map):
        url_map.add(Rule(
            '/schemas/<path:path>',
            endpoint=endpoint_get_schema,
            host='cdslabs.cern.ch'
        ))


@pytest.fixture()
def deposit_metadata():
    """General deposit metadata."""
    return {
        'category': 'CERN',
        'type': 'MOVIE',
        "contributors": [
            {
                "affiliations": [
                    "University of FuuBar"
                ],
                "email": "test_foo@cern.ch",
                "ids": [
                    {
                        "source": "cern",
                        "value": "12345"
                    },
                    {
                        "source": "cds",
                        "value": "67890"
                    }
                ],
                "name": "Do, John",
                "role": "Camera Operator"
            }
        ],
        '_cds': {}
    }


@pytest.fixture()
def project_deposit_metadata(deposit_metadata):
    """Project deposit metadata."""
    metadata = {
        'title': {
            'title': 'my project',
            'subtitle': 'tempor quis elit mollit',
        },
        'description': 'in tempor reprehenderit enim eiusmod',
        'contributors': [
            {
                'name': 'amet',
                'role': 'Editor'
            },
            {
                'name': 'in tempor reprehenderit enim eiusmod',
                'role': 'Camera Operator',
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
        description='in tempor reprehenderit enim eiusmod',
        featured=True,
        language='en',
        date='2016-12-03T00:00:00Z',
    )
    metadata.update(deposit_metadata)
    return metadata


@pytest.fixture()
def video_record_metadata(db, project_published, extra_metadata):
    """Video record metadata."""
    video = project_published[1]
    bucket_id = video['_buckets']['deposit']
    # Create video objects in bucket
    master = 'test.mp4'
    qualities = ['240', '360', '480', '720']
    filesize = 123456
    slaves = ['test[{}p]'.format(quality) for quality in qualities]
    test_stream = BytesIO(b'\x00' * filesize)
    with db.session.begin_nested():
        master_id = str(ObjectVersion.create(bucket_id, master,
                                             stream=test_stream).version_id)
        slave_ids = [str(ObjectVersion.create(bucket_id, slave,
                                              stream=test_stream).version_id)
                     for slave in slaves]
    db.session.commit()

    metadata = {
        '_files': [
            dict(
                bucket_id=bucket_id,
                context_type='master',
                media_type='video',
                content_type='mp4',
                checksum=rand_md5(),
                completed=True,
                key=master,
                frame=[
                    dict(
                        bucket_id=bucket_id,
                        checksum=rand_md5(),
                        completed=True,
                        key='frame-{}.jpg'.format(i),
                        links=dict(self='/api/files/...'),
                        progress=100,
                        size=filesize,
                        tags=dict(
                            master=master_id,
                            type='frame',
                            timestamp=(float(i) / 11) * 60.095
                        ),
                        version_id=rand_version_id())
                    for i in range(1, 11)
                ],
                tags=dict(
                    bit_rate='11915822',
                    width='4096',
                    height='2160',
                    uri_origin='https://test_domain.ch/test.mp4',
                    duration='60.095',),
                subformat=[
                    dict(
                        bucket_id=bucket_id,
                        context_type='subformat',
                        media_type='video',
                        content_type='mp4',
                        checksum=rand_md5(),
                        completed=True,
                        key=slaves[i],
                        links=dict(self='/api/files/...'),
                        progress=100,
                        size=filesize,
                        tags=dict(
                            _sorenson_job_id=rand_version_id(),
                            master=master_id,
                            preset_quality='{}p'.format(qualities[i]),
                            width=1000,
                            height=qualities[i],
                            smil=True,
                            video_bitrate=123456, ),
                        version_id=slave_id,)
                    for i, slave_id in enumerate(slave_ids)
                ],
                playlist=[
                    dict(
                        bucket_id=bucket_id,
                        context_type='playlist',
                        media_type='text',
                        content_type='smil',
                        checksum=rand_md5(),
                        completed=True,
                        key='test.smil',
                        links=dict(
                            self='/api/files/...'),
                        progress=100,
                        size=12355,
                        tags=dict(master=master_id),
                        version_id=rand_version_id(),)
                ],
            )
        ],
    }
    metadata.update(extra_metadata)
    metadata.update({k: video[k] for k in video.keys()
                     if k not in metadata.keys()})
    return metadata


@pytest.fixture()
def _deposit_metadata():
    """Extra metadata for record['_deposit']."""
    return {
        'extracted_metadata': {
            'tags': {
                'compatible_brands': 'qt  ',
                'creation_time': '1970-01-01T00:00:00.000000Z',
                'encoder': 'Lavf52.93.0',
                'major_brand': 'qt  ',
                'minor_version': '512',
            },
        }
    }


@pytest.fixture()
def extra_metadata():
    """Extra metadata."""
    return {
        'contributors': [
            {'name': 'paperone', 'role': 'Director'},
            {'name': 'topolino', 'role': 'Music by'},
            {'name': 'nonna papera', 'role': 'Producer'},
            {'name': 'pluto', 'role': 'Director'},
            {'name': 'zio paperino', 'role': 'Producer'}
        ],
        'license': [{
            'license': 'GPLv2',
            'url': 'http://license.cern.ch',
        }],
        'keywords': [
            {
                'source': 'source1',
                'name': 'keyword1',
            },
            {
                'source': 'source2',
                'name': 'keyword2',
            }
        ],
        'copyright': {
            'holder': 'CERN',
            'url': 'http://cern.ch',
            'year': '2017'
        },
        'title': {
            'title': 'My <b>english</b> title'
        },
        'title_translations': [
            {
                'language': 'fr',
                'title': 'My french title',
            }
        ],
        'description_translations': [
            {
                'language': 'fr',
                'value': 'france caption',
            }
        ],
        'language': 'en',
        'publication_date': '2017-03-02',
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
def json_partial_project_headers(app):
    """JSON headers for partial project deposits."""
    return [('Content-Type', 'application/vnd.project.partial+json'),
            ('Accept', 'application/json')]


@pytest.fixture()
def json_partial_video_headers(app):
    """JSON headers for partial video deposits."""
    return [('Content-Type', 'application/vnd.video.partial+json'),
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
def api_project(api_app, es, users, location, db, deposit_metadata):
    """New project with videos."""
    return new_project(api_app, es, cds_jsonresolver, users,
                       location, db, deposit_metadata)


@pytest.fixture()
def project_published(api_app, api_project, users):
    """New published project with videos."""
    (project, video_1, video_2) = api_project
    with api_app.test_request_context():
        # login as user_1
        login_user(User.query.get(users[0]))
        prepare_videos_for_publish([video_1, video_2])
        new_project = project.publish()
        new_videos = [record_resolver.resolve(id_)[1]
                      for id_ in new_project.video_ids]
        assert len(new_videos) == 2
    return (new_project,
            Video.get_record(new_videos[0].id),
            Video.get_record(new_videos[1].id))


@pytest.fixture()
def api_project_published(api_app, api_project, users):
    """New published project with videos."""
    (project, video_1, video_2) = api_project
    with api_app.test_request_context():
        login_user(User.query.get(users[0]))
        prepare_videos_for_publish([video_1, video_2])
        new_project = project.publish()
        new_videos = [record_resolver.resolve(id_)[1]
                      for id_ in new_project.video_ids]
        assert len(new_videos) == 2
    return (new_project,
            Video.get_record(new_videos[0].id),
            Video.get_record(new_videos[1].id))


@pytest.fixture()
def video_published(app, project_published):
    """New published project with videos."""
    return project_published[1]


@pytest.fixture()
def mock_sorenson():
    """Mock requests to the Sorenson server."""
    def mocked_encoding(input_file, output_file, preset_name, aspect_ratio,
                        max_height=None, max_width=None):
        # Check if options are valid
        try:
            ar, preset_config = _get_quality_preset(preset_name, aspect_ratio,
                                                    max_height, max_width)
        except InvalidResolutionError as e:
            raise e

        # just copy file
        shutil.copyfile(input_file, '{0}.mp4'.format(output_file))
        return '1234', ar, preset_config

    mock.patch(
        'cds.modules.flows.tasks.sorenson.start_encoding'
    ).start().side_effect = mocked_encoding

    mock.patch(
        'cds.modules.flows.tasks.sorenson.get_encoding_status'
    ).start().side_effect = [
        ('Waiting', 0),
        ('Transcoding', 45),
        ('Transcoding', 95),
        ('Finished', 100),
    ] * 50  # repeat for multiple usages of the mocked method

    mock.patch(
        'cds.modules.flows.tasks.sorenson.stop_encoding'
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


@pytest.fixture()
def keyword_1(api_app, es, indexer, pidstore):
    """Create a fixture for keyword."""
    data = {
        'key_id': '1',
        'name': '13 TeV',
    }
    return create_keyword(data=data)


@pytest.fixture()
def keyword_2(api_app, es, indexer, pidstore):
    """Create a fixture for keyword."""
    data = {
        'key_id': '2',
        'name': 'Accelerating News',
    }
    return create_keyword(data=data)


@pytest.fixture()
def keyword_3_deleted(api_app, es, indexer, pidstore):
    """Create a fixture for keyword."""
    data = {
        'key_id': '3',
        'name': 'Deleted Keyword',
        'deleted': True
    }
    return create_keyword(data=data)


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
    # FIXME check where it's used, and substitute with get_local_file
    # if is involved a video!
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


@pytest.yield_fixture(scope='session')
def test_videos_project():
    """Load test JSON records containing videos and a project."""
    with open(join(dirname(__file__),
                   '../data/test_videos_projects.json')) as fp:
        records = json.load(fp)
    yield records


@pytest.yield_fixture()
def test_video_records(db, test_videos_project):
    """Load test videos and project records."""
    result = []
    for r in test_videos_project:
        result.append(create_record(r))
    db.session.commit()
    yield result


@pytest.yield_fixture()
def indexed_videos(es, indexer, test_video_records):
    """Get a function to wait for records to be flushed to index."""
    RecordIndexer().bulk_index([record.id for _, record in test_video_records])
    RecordIndexer().process_bulk_queue()
    sleep(2)
    yield test_video_records


@pytest.fixture()
def cern_keywords():
    """Cern fixtures."""
    return {
        "tags": [
            {"id": "751",
             "name": "13 TeV"},
            {"id": "856",
             "name": "Accelerating News"},
            {"id": "97",
             "name": "accelerator"},
            {"id": "14",
             "name": "AEGIS"},
        ]
    }


@pytest.fixture()
def licenses():
    """List of licenses."""
    return {
        "AAL": {
            "domain_content": False,
            "domain_data": False,
            "domain_software": True,
            "family": "",
            "id": "AAL",
            "maintainer": "",
            "od_conformance": "not reviewed",
            "osd_conformance": "approved",
            "status": "active",
            "title": "Attribution Assurance Licenses",
            "url": "http://www.opensource.org/licenses/AAL"
        },
        "AFL-3.0": {
            "domain_content": True,
            "domain_data": False,
            "domain_software": True,
            "family": "",
            "id": "AFL-3.0",
            "maintainer": "Lawrence Rosen",
            "od_conformance": "not reviewed",
            "osd_conformance": "approved",
            "status": "active",
            "title": "Academic Free License 3.0",
            "url": "http://www.opensource.org/licenses/AFL-3.0"
        },
        "AGPL-3.0": {
            "domain_content": False,
            "domain_data": False,
            "domain_software": True,
            "family": "",
            "id": "AGPL-3.0",
            "maintainer": "Free Software Foundation",
            "od_conformance": "not reviewed",
            "osd_conformance": "approved",
            "status": "active",
            "title": "GNU Affero General Public License v3",
            "url": "http://www.opensource.org/licenses/AGPL-3.0"
        }
    }


@pytest.fixture()
def demo_ffmpeg_metadata():
    """Demo metadata extracted from ffmpeg."""
    keywords = ("21-07-16,cds,timelapseSM18,magnet on SM18,2 mqxfs quadrupole "
                "coils: winding completed and waiting for heat treatment")
    return {
        "streams": [
            {
                "index": 0,
                "codec_name": "prores",
                "codec_long_name": "Apple ProRes (iCodec Pro)",
                "codec_type": "video",
                "codec_time_base": "1/25",
                "codec_tag_string": "apch",
                "codec_tag": "0x68637061",
                "width": 3840,
                "height": 2160,
                "coded_width": 3840,
                "coded_height": 2160,
                "has_b_frames": 0,
                "sample_aspect_ratio": "1:1",
                "display_aspect_ratio": "16:9",
                "pix_fmt": "yuv422p10le",
                "level": -99,
                "color_space": "bt709",
                "color_transfer": "bt709",
                "color_primaries": "bt709",
                "field_order": "progressive",
                "refs": 1,
                "r_frame_rate": "25/1",
                "avg_frame_rate": "25/1",
                "time_base": "1/2500",
                "start_pts": 0,
                "start_time": "0.000000",
                "duration_ts": 1472300,
                "duration": "588.920000",
                "bit_rate": "732390489",
                "bits_per_raw_sample": "10",
                "nb_frames": "14723",
                "disposition": {
                    "default": 1,
                    "dub": 0,
                    "original": 0,
                    "comment": 0,
                    "lyrics": 0,
                    "karaoke": 0,
                    "forced": 0,
                    "hearing_impaired": 0,
                    "visual_impaired": 0,
                    "clean_effects": 0,
                    "attached_pic": 0,
                    "timed_thumbnails": 0
                },
                "tags": {
                    "creation_time": "2017-03-23T13:25:03.000000Z",
                    "language": "und",
                    "handler_name": "Core Media Data Handler",
                    "encoder": "Apple ProRes 422 HQ",
                    "timecode": "00:00:00:00"
                }
            }
        ],
        "format": {
            "filename": "CERN-FOOTAGE-2017-017-001.mov",
            "nb_streams": 3,
            "nb_programs": 0,
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "format_long_name": "QuickTime / MOV",
            "start_time": "0.000000",
            "duration": "588.920000",
            "size": "54115322362",
            "bit_rate": "735112712",
            "probe_score": 100,
            "tags": {
                "major_brand": "qt  ",
                "minor_version": "0",
                "compatible_brands": "qt  ",
                "creation_time": "2017-03-23T13:25:02.000000Z",
                "com.apple.quicktime.keywords": keywords,
                "com.apple.quicktime.description":
                "This video is about Quadrupole",
                "com.apple.quicktime.author": "MACVMO04",
                "com.apple.quicktime.displayname": "Quadrupole",
                "com.apple.quicktime.title": "Quadrupole"
            }
        }
    }


@pytest.fixture()
def current_year():
    """Returns the current year."""
    return str(datetime.now().year)
