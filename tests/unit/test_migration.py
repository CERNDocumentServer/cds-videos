# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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
import os

from os.path import join

from datetime import datetime
from invenio_db import db
from click.testing import CliRunner
from invenio_records.models import RecordMetadata
from invenio_records import Record
from invenio_pidstore.resolver import Resolver
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_pidstore.providers.datacite import DataCiteProvider
from invenio_files_rest.models import as_bucket, FileInstance, ObjectVersion
from invenio_sequencegenerator.models import Counter, TemplateDefinition
from invenio_accounts.models import User
from flask_security import login_user

from cds.cli import cli
from cds.modules.records.symlinks import SymlinksCreator
from cds.modules.migrator.records import CDSRecordDump, CDSRecordDumpLoader
from cds.modules.deposit.api import Project, Video, deposit_video_resolver, \
    deposit_project_resolver
from cds.modules.records.api import dump_object, CDSVideosFilesIterator, \
    CDSRecord
from cds.modules.webhooks.tasks import ExtractMetadataTask, ExtractFramesTask
from cds.modules.migrator.cli import \
    sequence_generator as cli_sequence_generator

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


def test_migrate_pids(app, location, datadir, users):
    """Test migrate pids."""
    data = load_json(datadir, 'cds_records_demo_1_project.json')
    dump = CDSRecordDump(data=data[0])
    record = CDSRecordDumpLoader.create(dump=dump)

    pids = [pid.pid_value for pid in
            PersistentIdentifier.query.filter_by(object_uuid=record.id)]
    expected = sorted(['2093596', 'CERN-MOVIE-2012-193'])
    assert sorted(pids) == expected


def test_migrate_record(api_app, location, datadir, es, users):
    """Test migrate date."""
    # [[ migrate the project ]]
    data = load_json(datadir, 'cds_records_demo_1_project.json')
    dump = CDSRecordDump(data=data[0])
    project = CDSRecordDumpLoader.create(dump=dump)
    p_id = project.id

    date = '2016-01-05'
    assert project['$schema'] == Project.get_record_schema()
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
        'modified_by': users[0],
    }

    # check project deposit
    deposit_project_uuid = PersistentIdentifier.query.filter_by(
        pid_type='depid', object_type='rec').one().object_uuid
    deposit_project = Record.get_record(deposit_project_uuid)
    assert Project._schema in deposit_project['$schema']
    assert project.revision_id == deposit_project[
        '_deposit']['pid']['revision_id']
    assert deposit_project['_deposit']['created_by'] == 1
    assert deposit_project['_deposit']['owners'] == [1]
    assert deposit_project['_files'] == []

    # [[ migrate the video ]]
    data = load_json(datadir, 'cds_records_demo_1_video.json')
    dump = CDSRecordDump(data=data[0])

    def check_symlinks(video):
        symlinks_creator = SymlinksCreator()
        files = list(symlinks_creator._get_list_files(record=video))
        assert len(files) == 1
        for file_ in files:
            path = symlinks_creator._build_link_path(
                symlinks_creator._symlinks_location, video, file_['key'])
            assert os.path.lexists(path)

    def check_gif(video, mock_gif):
        [call1, call2] = mock_gif.mock_calls
        # check gif record
        video = CDSRecord(dict(video), video.model)
        (_, _, args) = call1
        master_video = CDSVideosFilesIterator.get_master_video_file(video)
        assert args['master_id'] == master_video['version_id']
        assert args['bucket'].id == video.files.bucket.id
        assert len(args['frames']) == 10
        assert 'output_dir' in args
        # check gif deposit
        deposit = deposit_video_resolver(video['_deposit']['id'])
        (_, _, args) = call2
        master_video = CDSVideosFilesIterator.get_master_video_file(deposit)
        assert args['master_id'] == master_video['version_id']
        assert args['bucket'].id == deposit.files.bucket.id
        assert len(args['frames']) == 10
        assert 'output_dir' in args

    def load_video(*args, **kwargs):
        path = join(datadir, 'test.mp4')
        return open(path, 'rb'), None  # getsize(path)

    with mock.patch.object(DataCiteProvider, 'register'), \
            mock.patch.object(
                ExtractFramesTask, '_create_gif') as mock_gif, \
            mock.patch.object(
                CDSRecordDumpLoader, '_get_migration_file_stream_and_size',
                return_value=load_video()):
        video = CDSRecordDumpLoader.create(dump=dump)
        # assert mock_datacite.called is True
    # check smil file
    smil_obj = ObjectVersion.query.filter_by(
        key='CERN-MOVIE-2012-193-001.smil', is_head=True).one()
    storage = smil_obj.file.storage()
    assert '<video src' in storage.open().read().decode('utf-8')
    # check video symlinks
    check_symlinks(video)
    # check gif
    check_gif(video, mock_gif)
    # check project
    project = Record.get_record(p_id)
    assert project['videos'] == [
        {'$ref': 'https://cds.cern.ch/api/record/1495143'}
    ]
    assert video['$schema'] == Video.get_record_schema()
    date = '2017-07-13'
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
    assert video['_cds']['state'] == {
        "file_transcode": "SUCCESS",
        "file_video_extract_frames": "SUCCESS",
        "file_video_metadata_extraction": "SUCCESS"
    }
    assert 'extracted_metadata' in video['_cds']

    def check_files(video):
        bucket = CDSRecordDumpLoader._get_bucket(record=video)
        files = [dump_object(obj)
                 for obj in ObjectVersion.get_by_bucket(bucket=bucket)]
        for file_ in files:
            assert as_bucket(file_['bucket_id']) is not None
            assert 'checksum' in file_
            assert 'content_type' in file_
            assert 'context_type' in file_
            assert FileInstance.query.filter_by(
                id=file_['file_id']) is not None
            assert 'key' in file_
            assert 'links' in file_
            assert 'content_type' in file_
            assert 'context_type' in file_
            assert 'media_type' in file_
            assert 'tags' in file_

        # check extracted metadata
        master_video = CDSVideosFilesIterator.get_master_video_file(video)
        assert any([key in master_video['tags']
                    for key in ExtractMetadataTask._all_keys])
        assert any([key in video['_cds']['extracted_metadata']
                    for key in ExtractMetadataTask._all_keys])

    def check_buckets(record, deposit):
        def get(key, record):
            bucket = CDSRecordDumpLoader._get_bucket(record=record)
            files = [dump_object(obj)
                     for obj in ObjectVersion.get_by_bucket(bucket=bucket)]
            return [file_[key] for file_ in files]

        def check(record, deposit, file_key, different=None):
            values_record = set(get(file_key, record))
            values_deposit = set(get(file_key, deposit))
            difference = len(values_record - values_deposit)
            assert different == difference

        def check_tag_master(record):
            bucket = CDSRecordDumpLoader._get_bucket(record=record)
            master = CDSVideosFilesIterator.get_master_video_file(record)
            files = [dump_object(obj)
                     for obj in ObjectVersion.get_by_bucket(bucket=bucket)
                     if obj.get_tags().get('master')]
            assert all([file_['tags']['master'] == master['version_id']
                        for file_ in files])

        # 1 bucket record != 1 bucket deposit
        check(record, deposit, 'bucket_id', 1)
        # all file_id are the same except the smil file (only in record)
        check(record, deposit, 'file_id', 1)
        check(record, deposit, 'key', 1)
        # 18 object_version record != 17 object_version deposit
        check(record, deposit, 'version_id', 18)
        # check tag 'master' where is pointing
        check_tag_master(record)
        check_tag_master(deposit)

    def check_first_level_files(record):
        [master] = [file_ for file_ in deposit_video['_files']
                    if file_['context_type'] == 'master']
        assert len(master['subformat']) == 5
        assert len(master['frame']) == 10
        # TODO assert len(master['playlist']) == ??
        assert len([file_ for file_ in deposit_video['_files']
                    if file_['context_type'] == 'master']) == 1
        duration = float(record['_cds']['extracted_metadata']['duration'])
        for frame in master['frame']:
            assert float(frame['tags']['timestamp']) < duration
            assert float(frame['tags']['timestamp']) > 0
        # check tag 'preset_quality'
        pqs = [form['tags']['preset_quality'] for form in master['subformat']]
        assert sorted(pqs) == sorted(['1080p', '240p', '360p', '480p', '720p'])
        # check tag 'display_aspect_ratio'
        dar = set([form['tags']['display_aspect_ratio']
                   for form in master['subformat']])
        assert dar == {'16:9'}

    # check video deposit
    deposit_video_uuid = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_type == 'depid',
        PersistentIdentifier.object_uuid != str(deposit_project_uuid),
        PersistentIdentifier.object_type == 'rec'
    ).one().object_uuid
    deposit_video = Video.get_record(str(deposit_video_uuid))
    assert Video._schema in deposit_video['$schema']
    assert video.revision_id == deposit_video[
        '_deposit']['pid']['revision_id']
    assert deposit_video['_deposit']['created_by'] == users[0]
    assert deposit_video['_deposit']['owners'] == [users[0]]
    assert deposit_video['_project_id'] == '2093596'
    assert len(video['_files']) == 2
    assert len(deposit_video['_files']) == 2
    check_files(video)
    check_files(deposit_video)
    check_buckets(video, deposit_video)
    check_first_level_files(video)
    check_first_level_files(deposit_video)

    # try to edit video
    deposit_video = deposit_video_resolver(deposit_video['_deposit']['id'])
    deposit_video = deposit_video.edit()

    # try to edit project
    deposit_project = deposit_project_resolver(
        deposit_project['_deposit']['id'])
    deposit_project = deposit_project.edit()

    login_user(User.query.filter_by(id=users[0]).first())
    deposit_video['title']['title'] = 'test'
    deposit_video = deposit_video.publish()
    _, record_video = deposit_video.fetch_published()
    assert record_video['title']['title'] == 'test'


def test_sequence_number_update_after_migration(app, location, script_info):
    """Test sequence number update after migration."""
    # simulate a import of record < now(year)
    pid11 = PersistentIdentifier(
        pid_type='recid', pid_value='2093596', status=PIDStatus.REGISTERED,
        object_type='rec', object_uuid='e5428b04324b4c9fbfed02fbf78bb959')
    pid12 = PersistentIdentifier(
        pid_type='rn', pid_value='CERN-MOVIE-2012-193',
        status=PIDStatus.REGISTERED,
        object_type='rec', object_uuid='e5428b04324b4c9fbfed02fbf78bb959')
    db.session.add(pid11)
    db.session.add(pid12)
    db.session.commit()

    # run seq number update
    runner = CliRunner()
    res = runner.invoke(cli_sequence_generator, [], obj=script_info)

    # no counter should be created
    assert res.exit_code == 0
    assert Counter.query.all() == []
    assert len(TemplateDefinition.query.all()) == 2

    # simulate a import of record == now(year)
    year = datetime.now().year
    pid11 = PersistentIdentifier(
        pid_type='recid', pid_value='2093597', status=PIDStatus.REGISTERED,
        object_type='rec', object_uuid='e5428b04324b4c9fbfed02fbf78bb950')
    pid12 = PersistentIdentifier(
        pid_type='rn', pid_value='CERN-MOVIE-{0}-5'.format(year),
        status=PIDStatus.REGISTERED,
        object_type='rec', object_uuid='e5428b04324b4c9fbfed02fbf78bb959')
    db.session.add(pid11)
    db.session.add(pid12)
    db.session.commit()

    # run seq number update
    runner = CliRunner()
    res = runner.invoke(cli_sequence_generator, [], obj=script_info)

    # no counter should be created
    assert res.exit_code == 0
    [counter] = Counter.query.all()
    assert counter.counter == 6
    assert counter.definition_name == 'project-v1_0_0'
    assert counter.template_instance == 'CERN-MOVIE-2017-{counter}'
    assert len(TemplateDefinition.query.all()) == 2


def test_retry_run_extracted_metadata(app):
    """Test retry is working properly."""
    with mock.patch.object(
            ExtractMetadataTask, 'create_metadata_tags',
            side_effect=Exception):
        with pytest.raises(Exception):
            CDSRecordDumpLoader._run_extracted_metadata(master={}, retry=1)
