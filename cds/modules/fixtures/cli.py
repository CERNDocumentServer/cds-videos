# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Fixture Modules."""

from __future__ import absolute_import, print_function

import copy
import json
import os
import shutil
import tarfile
import tempfile
import uuid

import click
import pkg_resources
import requests
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_files_rest.models import (Bucket, Location, ObjectVersion,
                                       ObjectVersionTag)
from invenio_indexer.api import RecordIndexer
from invenio_opendefinition.tasks import (harvest_licenses,
                                          import_licenses_from_json)
from invenio_pages import Page
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records_files.models import RecordsBuckets
from invenio_sequencegenerator.api import Template

from ..records.minters import catid_minter
from ..records.api import Category, CDSVideosFilesIterator
from ..records.serializers.smil import generate_smil_file


from ..records.api import CDSRecord as Record
from ..records.tasks import keywords_harvesting


def _load_json_source(filename):
    """Load json fixture."""
    source = pkg_resources.resource_filename(
        'cds.modules.fixtures', 'data/{0}'.format(filename)
    )
    with open(source, 'r') as fp:
        content = json.load(fp)
    return content


def _index(iterator):
    """Bulk index the iterator."""
    indexer = RecordIndexer()
    indexer.bulk_index(iterator)
    indexer.process_bulk_queue()


def _process_files(record, files_metadata):
    """Attach files to a record with a given metadata.

    Assumptions:
    - The source must be a URL pointing to a tar file.
    - All files listed in the metadata are inside the source tar.
    - Master files are listed before slaves.
    - The reference from the slave to master is done via key.
    """
    if not files_metadata:
        return
    bucket = Bucket.create(location=Location.get_by_name('videos'))
    RecordsBuckets.create(record=record.model, bucket=bucket)
    response = requests.get(
        files_metadata['source'], stream=True, verify=False)

    # Throw an error for bad status codes
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as f:
        for chunk in response:
            f.write(chunk)
    tar = tarfile.open(name=f.name)
    tar.extractall(path=tempfile.gettempdir())
    files_base_dir = os.path.join(tempfile.gettempdir(), tar.getnames()[0])
    tar.close()
    os.remove(f.name)

    for f in files_metadata['metadata']:
        obj = ObjectVersion.create(bucket, f['key'])
        with open(os.path.join(files_base_dir, f['key']), 'rb') as fp:
            obj.set_contents(fp)
        for k, v in f['tags'].items():
            if k == 'master':
                v = ObjectVersion.get(bucket, v).version_id
            ObjectVersionTag.create(obj, k, v)
    shutil.rmtree(files_base_dir)

    record['_files'] = record.files.dumps()


def _mint_pids(record):
    """Mint available PIDs."""
    # TODO: refactor to get list of dicts with the parameters to pass to create
    # TODO: can we update the sequences for the report number?
    PersistentIdentifier.create(
        pid_type='recid',
        pid_value=record['recid'],
        pid_provider=None,
        object_type='rec',
        object_uuid=record.id,
        status=PIDStatus.REGISTERED
    )
    PersistentIdentifier.create(
        pid_type='rn',
        pid_value=record['report_number'][0],
        pid_provider=None,
        object_type='rec',
        object_uuid=record.id,
        status=PIDStatus.REGISTERED
    )


@click.group()
def fixtures():
    """Create initial data and demo records."""


@fixtures.command()
@with_appcontext
def records():
    """Load demo records."""
    to_index = []
    for project_file in pkg_resources.resource_listdir(
            'cds.modules.fixtures', os.path.join('data', 'videos')):
        project_data = _load_json_source(os.path.join('videos', project_file))
        with db.session.begin_nested():
            files_metadata = copy.deepcopy(project_data.get('_files'))
            project_data['_files'] = []
            project = Record.create(data=project_data)
            _mint_pids(project)
            to_index.append(project.id)
            videos = copy.deepcopy(project.get('videos'))
            project['videos'] = []
            _process_files(project, files_metadata)
            for video_data in videos:
                files_metadata = copy.deepcopy(video_data.get('_files'))
                video_data['_files'] = []
                video = Record.create(data=video_data)
                _mint_pids(video)
                to_index.append(video.id)
                video['_project_id'] = str(project['recid'])
                _process_files(video, files_metadata)
                # FIXME probably there is a better way to create the smil file
                master_video = CDSVideosFilesIterator.get_master_video_file(
                    video)
                generate_smil_file(
                    video['recid'], video,
                    master_video['bucket_id'], master_video['version_id'],
                    skip_schema_validation=True
                )
                video['_files'] = video.files.dumps()

                project['videos'].append({
                    '$ref':
                    'https://cds.cern.ch/api/record/{0}'.format(video['recid'])
                })
                video.commit()
            project.commit()
        db.session.commit()

    _index(to_index)
    click.echo('DONE :)')


@fixtures.command()
@with_appcontext
def categories():
    """Load categories."""
    categories = _load_json_source('categories.json')

    # save in db
    to_index = []
    with db.session.begin_nested():
        for data in categories:
            cat_id = uuid.uuid4()
            catid_minter(cat_id, data)
            category = Category.create(data, id_=cat_id)
            to_index.append(category.id)
    db.session.commit()

    # index them
    _index(to_index)
    click.echo('DONE :)')


@fixtures.command()
@with_appcontext
def sequence_generator():
    """Register CDS templates for sequence generation."""
    with db.session.begin_nested():
        Template.create(name='project-v1_0_0',
                        meta_template='{category}-{type}-{year}-{counter:03d}',
                        start=1)
        Template.create(name='video-v1_0_0',
                        meta_template='{project-v1_0_0}-{counter:03d}',
                        start=1)
    db.session.commit()
    click.echo('DONE :)')


@fixtures.command()
@with_appcontext
def pages():
    """Register CDS static pages."""
    def page_data(page):
        return pkg_resources.resource_stream(
            'cds.modules.fixtures', os.path.join('data/pages', page)
        ).read().decode('utf8')

    pages = [
        Page(url='/about',
             title='About',
             description='About',
             content=page_data('about.html'),
             template_name='invenio_pages/dynamic.html'),
        Page(url='/contact',
             title='Contact',
             description='Contact',
             content=page_data('contact.html'),
             template_name='invenio_pages/dynamic.html'),
        Page(url='/faq',
             title='FAQ',
             description='FAQ',
             content=page_data('faq.html'),
             template_name='invenio_pages/dynamic.html'),
        Page(url='/feedback',
             title='Feedback',
             description='Feedback',
             content=page_data('feedback.html'),
             template_name='invenio_pages/dynamic.html'),
        Page(url='/help',
             title='Help',
             description='Help',
             content=page_data('help.html'),
             template_name='invenio_pages/dynamic.html'),
        Page(url='/terms',
             title='Terms of Use',
             description='Terms of Use',
             content=page_data('terms_of_use.html'),
             template_name='invenio_pages/dynamic.html')
    ]
    with db.session.begin_nested():
        Page.query.delete()
        db.session.add_all(pages)
    db.session.commit()
    click.echo('DONE :)')


@fixtures.command()
@click.option('--url', '-u')
@with_appcontext
def keywords(url):
    """Load keywords."""
    if url:
        current_app.config['CDS_KEYWORDS_HARVESTER_URL'] = url

    keywords_harvesting.s().apply()
    click.echo('DONE :)')


@fixtures.command()
@with_appcontext
def licenses():
    """Load Licenses."""
    # harvest licenses
    harvest_licenses()
    # load cds licenses
    import_licenses_from_json(_load_json_source('licenses.json'))
    db.session.commit()
    # index all licenses
    query = (str(x[0]) for x in PersistentIdentifier.query.filter_by(
        pid_type='od_lic').values(PersistentIdentifier.object_uuid))
    _index(query)
    click.echo('DONE :)')
