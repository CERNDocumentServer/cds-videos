# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

import click
import pkg_resources
import tarfile
import uuid
from os.path import join

from flask_cli import with_appcontext

from dojson.contrib.marc21 import marc21
from dojson.contrib.marc21.utils import create_record, split_blob

from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_pidstore import current_pidstore
from invenio_records.api import Record


def _untar(source, destination='/tmp'):
    """Untar in location."""
    tar = tarfile.open(source)
    tar.extractall(destination)
    tar.close()
    source = join(destination, 'theses')
    return source


@click.group()
def fixtures():
    """Create demo records."""


@fixtures.command()
@with_appcontext
def invenio():
    """Invenio demo records."""
    click.echo('Loading data...')
    # pkg resources the demodata
    data_path = pkg_resources.resource_filename(
        'invenio_records', 'data/marc21/bibliographic.xml'
    )

    with open(data_path) as source:
        indexer = RecordIndexer()
        # FIXME: Add some progress
        # with click.progressbar(data) as records:
        with db.session.begin_nested():
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
        db.session.commit()
    click.echo('DONE :)')


@fixtures.command()
@click.option('--temp', '-t', default='/tmp')
@click.option('--source', '-s', default=False)
@with_appcontext
def cds(temp, source):
    """CDS demo records (From Theses Collection)."""
    click.echo('Loading data it may take several minutes.')
    # pkg resources the demodata
    if not source or source.contains('tar'):
        tar_path = pkg_resources.resource_filename(
            'cds.modules.fixtures', 'data/records.tar.gz'
        )
        source = _untar(tar_path)
    with open(source) as source:
        indexer = RecordIndexer()
        # FIXME: Add some progress
        # with click.progressbar(data) as records:
        with db.session.begin_nested():
            for index, data in enumerate(split_blob(source.read()), start=1):
                # create uuid
                rec_uuid = uuid.uuid4()
                # do translate
                record = marc21.do(create_record(data))
                del record['control_number']
                # create PID
                current_pidstore.minters['recid'](
                    rec_uuid, record
                )
                # create record
                indexer.index(Record.create(record, id_=rec_uuid))
        db.session.commit()
