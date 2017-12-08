# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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
"""Migration CLI."""

from __future__ import absolute_import, print_function

import json
from datetime import datetime

import click
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_migrator.cli import _loadrecord, dumps
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_pidstore.models import PersistentIdentifier
from invenio_sequencegenerator.api import Sequence
from .tasks import clean_record, check_record

from ...modules.deposit.api import Project


def load_records(sources, source_type, eager):
    """Load records."""
    for idx, source in enumerate(sources, 1):
        click.echo('Loading dump {0} of {1} ({2})'.format(
            idx, len(sources), source.name))
        data = json.load(source)
        with click.progressbar(data) as records:
            for item in records:
                count = PersistentIdentifier.query.filter_by(
                    pid_type='recid', pid_value=str(item['recid'])).count()
                if count > 0:
                    current_app.logger.warning(
                        "migration: duplicate {0}".format(item['recid']))
                else:
                    try:
                        _loadrecord(item, source_type, eager=eager)
                    except PIDAlreadyExists:
                        current_app.logger.warning(
                            "migration: report number associated with multiple"
                            "recid. See {0}".format(item['recid']))


@dumps.command()
@with_appcontext
def sequence_generator():
    """Update sequences according to current report numbers in pidstore."""

    def get_pids(year):
        """Get project and video pids registered this year."""
        query = PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_value.contains('-{0}-'.format(year)))
        pids = [pid.pid_value for pid in query.all()]
        videos = [pid for pid in pids if pid.count('-') == 4]
        projects = [pid for pid in pids if pid.count('-') == 3]
        # check no pids are lost
        assert sorted(pids) == sorted(projects + videos)
        return projects, videos

    def get_cats_types(projects, videos):
        """Get category/type list for projects and videos."""
        cats_types = set(["-".join(pid.split('-')[0:2]) for pid in projects])
        cats_types_video = set(
            ["-".join(pid.split('-')[0:2]) for pid in videos])
        # check category/type list are the same
        assert all([ct in cats_types for ct in cats_types_video])
        return cats_types

    def find_next(cat_type, pids):
        max_count = max([
            int(pid.split('-')[-1]) for pid in pids if pid.startswith(cat_type)
        ])
        return max_count + 1

    def update_counter(next_counter, **sequence_kwargs):
        """Update sequence counter."""
        counter = Sequence(**sequence_kwargs).counter
        counter.counter = next_counter
        db.session.add(counter)
        return counter

    year = datetime.now().year
    project_pids, video_pids = get_pids(year=year)
    cats_types = get_cats_types(project_pids, video_pids)

    for cat_type in cats_types:
        [cat, type_] = cat_type.split('-')
        update_counter(
            next_counter=find_next(cat_type, project_pids),
            **{
                'template': Project.sequence_name,
                'year': year,
                'category': cat,
                'type': type_
            })

    db.session.commit()


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@click.option(
    '--source-type',
    '-t',
    type=click.Choice(['json', 'marcxml']),
    default='marcxml',
    help='Whether to use JSON or MARCXML.')
@click.option(
    '--recid',
    '-r',
    help='Record ID to load (NOTE: will load only one record!).',
    default=None)
@with_appcontext
def dryrun(sources, source_type, recid):
    """Load records migration dump."""
    from invenio_logging.fs import InvenioLoggingFS
    current_app.config['LOGGING_FS'] = True
    current_app.config['LOGGING_FS_LOGFILE'] = '/tmp/migration.log'
    InvenioLoggingFS(current_app)
    current_app.config['MIGRATOR_RECORDS_DUMPLOADER_CLS'] = \
        'cds.modules.migrator.records:DryRunCDSRecordDumpLoader'
    load_records(sources=sources, source_type=source_type, eager=True)


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@click.option(
    '--source-type',
    '-t',
    type=click.Choice(['json', 'marcxml']),
    default='marcxml',
    help='Whether to use JSON or MARCXML.')
@click.option(
    '--recid',
    '-r',
    help='Record ID to load (NOTE: will load only one record!).',
    default=None)
@with_appcontext
def cleanrecords(sources, source_type, recid):
    """Clean everything a given dump has done."""
    if recid is not None:
        for source in sources:
            records = json.load(source)
            for item in records:
                if str(item['recid']) == str(recid):
                    clean_record.delay(item, source_type)
                    click.echo("Record '{recid}' cleaned.".format(recid=recid))
                    return
        click.echo("Record '{recid}' not found.".format(recid=recid))
    else:
        for idx, source in enumerate(sources, 1):
            click.echo('Loading dump {0} of {1} ({2})'.format(
                idx, len(sources), source.name))
            data = json.load(source)
            with click.progressbar(data) as records:
                for item in records:
                    clean_record.delay(item, source_type)


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@click.option(
    '--source-type',
    '-t',
    type=click.Choice(['json', 'marcxml']),
    default='marcxml',
    help='Whether to use JSON or MARCXML.')
@click.option(
    '--recid',
    '-r',
    help='Record ID to load (NOTE: will load only one record!).',
    default=None)
@with_appcontext
def run(sources, source_type, recid):
    """Load records migration dump."""
    load_records(sources=sources, source_type=source_type, eager=False)


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@click.option(
    '--source-type',
    '-t',
    type=click.Choice(['json', 'marcxml']),
    default='marcxml',
    help='Whether to use JSON or MARCXML.')
@with_appcontext
def checkrecords(sources, source_type):
    """Integrity check for records and files."""
    for idx, source in enumerate(sources, 1):
        click.echo('Loading dump {0} of {1} ({2})'.format(
            idx, len(sources), source.name))
        data = json.load(source)
        with click.progressbar(data) as records:
            for item in records:
                check_record.delay(item, source_type)
