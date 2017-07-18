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

"""CDS migration to CDSLabs tests."""

from __future__ import absolute_import, print_function

import pytest
import mock

from os.path import join

from click.testing import CliRunner
from invenio_records.models import RecordMetadata
from invenio_records import Record
from invenio_pidstore.resolver import Resolver
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.providers.datacite import DataCiteProvider

from cds.cli import cli
from cds.modules.migrator.records import CDSRecordDump, CDSRecordDumpLoader
from cds.modules.deposit.api import Project, Video, deposit_video_resolver, \
    deposit_project_resolver

from helpers import load_json


@pytest.mark.skip(reason='Wait fix cds-dojson')
def test_record_files_migration(app, location, script_info, datadir):
    """Test CDS records and files migrations."""
    runner = CliRunner()
    filepath = join(datadir, 'cds_records_and_files_dump.json')

    result = runner.invoke(
        cli, ['dumps', 'loadrecords', filepath], obj=script_info)
    assert result.exit_code == 0

    assert RecordMetadata.query.count() == 1

    # CERN Theses
    resolver = Resolver(
        pid_type='recid', object_type='rec', getter=Record.get_record)
    pid, record = resolver.resolve(1198695)

    assert record
    assert record.revision_id == 34  # 33 from the dump and 1 for the files
    assert record['main_entry_personal_name']['personal_name'] == 'Caffaro, J'
    assert 'CERN' in record['subject_indicator']
    assert record['control_number'] == '1198695'
    assert record['title_statement']['title'] == \
        'Improving the Formatting Tools of CDS Invenio'
    assert record['source_of_acquisition'][0]['stock_number'] == \
        'CERN-THESIS-2009-057'

    assert '_files' in record
    assert record['_files'][0]['key'] == 'CERN-THESIS-2009-057.pdf'
    assert record['_files'][0]['doctype'] == 'CTH_FILE'


def test_mingrate_pids(app, location, datadir):
    """Test migrate pids."""
    data = load_json(datadir, 'cds_records_demo_1_project.json')
    dump = CDSRecordDump(data=data[0])
    record = CDSRecordDumpLoader.create(dump=dump)

    pids = [pid.pid_value for pid in
            PersistentIdentifier.query.filter_by(object_uuid=record.id)]
    expected = sorted(['2093596', 'CERN-MOVIE-2012-193'])
    assert sorted(pids) == expected


def test_mingrate_date(app, location, datadir):
    """Test migrate date."""
    # create the project
    data = load_json(datadir, 'cds_records_demo_1_project.json')
    dump = CDSRecordDump(data=data[0])
    project = CDSRecordDumpLoader.create(dump=dump)
    p_id = project.id

    date = '2015-11-13'
    assert project['$schema'] == {'$ref': Project.get_record_schema()}
    assert project['date'] == date
    assert project['publication_date'] == date
    assert 'license' not in project
    assert 'copyright' not in project
    assert project['_cds'] == {
        "state": {
            "file_transcode": "SUCCESS",
            "file_video_extract_frames": "SUCCESS",
            "file_video_metadata_extraction": "SUCCESS"
        },
        # FIXME remove it
        'extracted_metadata': {'duration': 12},
    }

    # create the video
    data = load_json(datadir, 'cds_records_demo_1_video.json')
    dump = CDSRecordDump(data=data[0])
    with mock.patch.object(DataCiteProvider, 'register') \
            as mock_datacite:
        video = CDSRecordDumpLoader.create(dump=dump)
    assert mock_datacite.called is True
    project = Record.get_record(p_id)
    assert project['videos'] == [
        {'$ref': 'https://cds.cern.ch/api/record/1495143'}
    ]
    assert video['$schema'] == {'$ref': Video.get_record_schema()}
    date = '2012-11-20'
    assert video['date'] == date
    assert video['publication_date'] == date
    assert video['_project_id'] == '2093596'
    assert video['license'] == [{
        'license': 'CERN',
        'url': 'http://copyright.web.cern.ch',
    }]
    assert video['copyright'] == {
        'holder': 'CERN',
        'year': '2012',
        'url': 'http://copyright.web.cern.ch',
    }
    assert video['description'] == ''
    assert 'doi' in video
    assert video['_cds'] == {
        "state": {
            "file_transcode": "SUCCESS",
            "file_video_extract_frames": "SUCCESS",
            "file_video_metadata_extraction": "SUCCESS"
        },
        # FIXME remove it
        'extracted_metadata': {'duration': 12},
    }

    # check project deposit
    deposit_project = CDSRecordDumpLoader._create_deposit(record=project)
    assert Project._schema in deposit_project['$schema']
    assert project.revision_id == deposit_project[
        '_deposit']['pid']['revision_id']
    assert deposit_project['_deposit']['created_by'] == -1
    assert deposit_project['_deposit']['owners'] == [-1]

    # check video deposit
    deposit_video = CDSRecordDumpLoader._create_deposit(record=video)
    assert Video._schema in deposit_video['$schema']
    assert video.revision_id == deposit_video[
        '_deposit']['pid']['revision_id']
    assert deposit_video['_deposit']['created_by'] == -1
    assert deposit_video['_deposit']['owners'] == [-1]

    # try to edit video
    deposit_video = deposit_video_resolver(deposit_video['_deposit']['id'])
    deposit_video = deposit_video.edit()

    # try to edit project
    deposit_project = deposit_project_resolver(
        deposit_project['_deposit']['id'])
    deposit_project = deposit_project.edit()

    # try to publish again the video
    deposit_video['title']['title'] = 'test'
    deposit_video = deposit_video.publish()
    _, record_video = deposit_video.fetch_published()
    assert record_video['title']['title'] == 'test'
