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

"""Record Loader."""

from __future__ import absolute_import, print_function

import logging
import os
import shutil
import tempfile
from copy import deepcopy

import arrow
from cds_dojson.marc21 import marc21
from cds_dojson.marc21.utils import create_record
from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from invenio_deposit.minters import deposit_minter
from invenio_files_rest.models import (Bucket, FileInstance, Location,
                                       ObjectVersion, ObjectVersionTag,
                                       as_bucket, as_object_version)
from invenio_jsonschemas import current_jsonschemas
from invenio_migrator.records import RecordDump, RecordDumpLoader
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_records_files.models import RecordsBuckets

from ..deposit.api import Project, Video, record_unbuild_url
from ..deposit.tasks import datacite_register
from ..records.api import CDSVideosFilesIterator, dump_generic_object
from ..records.fetchers import report_number_fetcher
from ..records.minters import _doi_minter
from ..records.serializers.smil import generate_smil_file
from ..records.symlinks import SymlinksCreator
from ..records.validators import PartialDraft4Validator
from ..webhooks.tasks import ExtractFramesTask, ExtractMetadataTask
from ..xrootd.utils import eos_retry, replace_xrootd
from .utils import process_fireroles, update_access

logger = logging.getLogger('cds-record-migration')


class CDSRecordDump(RecordDump):
    """CDS record dump class."""

    def __init__(self,
                 data,
                 source_type='marcxml',
                 latest_only=False,
                 pid_fetchers=None,
                 dojson_model=marc21):
        """Initialize."""
        pid_fetchers = [
            report_number_fetcher
        ]
        super(self.__class__, self).__init__(data, source_type, latest_only,
                                             pid_fetchers, dojson_model)

    @property
    def collection_access(self):
        """Calculate the value of the `_access` key.

        Due to the way access rights were defined in Invenio legacy we can only
        calculate the value of this key at the moment of the dump, therefore
        only the access rights are correct for the last version.
        """
        read_access = set()
        for coll, restrictions in self.data['collections'][
                'restricted'].items():
            read_access.update(restrictions['users'])
            read_access.update(process_fireroles(restrictions['fireroles']))
        read_access.discard(None)

        return {'read': list(read_access)}

    def _prepare_intermediate_revision(self, data):
        """Convert intermediate versions to marc into JSON."""
        dt = arrow.get(data['modification_datetime']).datetime

        if self.source_type == 'marcxml':
            marc_record = create_record(data['marcxml'])
            return (dt, marc_record)
        else:
            val = data['json']

        # MARC21 versions of the record are only accessible to admins
        val['_access'] = {
            'read': ['cds-admin@cern.ch'],
            'update': ['cds-admin@cern.ch']
        }

        return (dt, val)

    def _prepare_final_revision(self, data):
        dt = arrow.get(data['modification_datetime']).datetime

        if self.source_type == 'marcxml':
            marc_record = create_record(data['marcxml'])
            try:
                val = self.dojson_model.do(marc_record)
            except Exception as e:
                current_app.logger.error(
                    'Impossible to convert to JSON {0} - {1}'.format(
                        e, marc_record))
                raise
            missing = self.dojson_model.missing(marc_record, _json=val)
            if missing:
                raise RuntimeError('Lossy conversion: {0}'.format(missing))
        else:
            val = data['json']

        # Calculate the _access key
        update_access(val, self.collection_access)

        return (dt, val)

    def prepare_revisions(self):
        """Prepare data.

        We don't convert intermediate versions to JSON to avoid conversion
        errors and get a lossless version migration.

        If the revisions is the last one, an error will be generated if the
        final translation is not complete.
        """
        # Prepare revisions
        self.revisions = []

        it = [self.data['record'][0]] if self.latest_only \
            else self.data['record']

        for i in it[:-1]:
            self.revisions.append(self._prepare_intermediate_revision(i))

        self.revisions.append(self._prepare_final_revision(it[-1]))


class CDSRecordDumpLoader(RecordDumpLoader):
    """Migrate a CDS record."""

    dependent_objs = ['frame', 'frames-preview', 'playlist', 'subformat']

    @classmethod
    def create_files(cls, *args, **kwargs):
        """Disable the files load."""
        pass

    @classmethod
    def create(cls, dump):
        """Update an existing record."""
        record = super(CDSRecordDumpLoader, cls).create(dump=dump)
        cls._resolve_publication_date(record=record)
        if Video.get_record_schema() == record['$schema']['$ref']:
            cls._resolve_license_copyright(record=record)
            cls._resolve_description(record=record)
            _doi_minter(record_uuid=record.id, data=record)
            cls._resolve_project_id(video=record)
        cls._resolve_cds(record=record)

        record.commit()
        db.session.commit()

        if Video.get_record_schema() == record['$schema']['$ref']:
            cls._resolve_datacite_register(record=record)
        record, deposit = cls._create_deposit(record=record)
        cls._create_symlinks(record=record)

        # commit!
        deposit.commit()
        record.commit()
        db.session.commit()
        return record

    @classmethod
    def _create_gif(cls, video):
        """Create GIF."""
        logging.debug('Create gif for {0}'.format(str(video.id)))
        # get master
        master_video = CDSVideosFilesIterator.get_master_video_file(video)
        # get deposit bucket
        bucket = cls._get_bucket(record=video)
        # open bucket
        was_locked = bucket.locked
        bucket.locked = False
        # get frames
        frames = [replace_xrootd(FileInstance.get(f['file_id']).uri)
                  for f in CDSVideosFilesIterator.get_video_frames(
            master_file=master_video)]
        logging.debug(
            'Create gif for {0} using {1}'.format(str(video.id), frames))
        # create GIF
        output_folder = tempfile.mkdtemp()
        ExtractFramesTask._create_gif(bucket=bucket, frames=frames,
                                      output_dir=output_folder,
                                      master_id=master_video['version_id'])
        shutil.rmtree(output_folder)
        # lock bucket
        bucket.locked = was_locked
        db.session.merge(bucket)

    @classmethod
    def _create_symlinks(cls, record):
        """Create symlinks."""
        logging.debug('Create symlinks')
        SymlinksCreator().create(prev_record=record, new_record=record)

    @classmethod
    def _resolve_project_id(cls, video):
        """Resolve project id."""
        video['_project_id'] = record_unbuild_url(video['_project_id'])

    @classmethod
    def _create_deposit(cls, record):
        """Create a deposit from the record."""
        logging.debug('Create deposit')
        data = deepcopy(record)
        cls._resolve_schema(deposit=data, record=record)
        deposit = Record.create(data, validator=PartialDraft4Validator)
        cls._resolve_deposit(deposit=deposit, record=record)
        cls._resolve_bucket(deposit=deposit, record=record)
        cls._resolve_files(deposit=deposit, record=record)
        # generate files list
        cls._resolve_dumps(record=record)
        #  db.session.commit()
        return record, deposit

    @classmethod
    @eos_retry(10)
    def _run_extracted_metadata(cls, master):
        """Run extract metadata from the video."""
        return ExtractMetadataTask.create_metadata_tags(
            object_=master, keys=ExtractMetadataTask._all_keys)

    @classmethod
    def _resolve_extracted_metadata(cls, deposit, record):
        """Extract metadata from the video."""
        master_video = CDSVideosFilesIterator.get_master_video_file(deposit)
        master = as_object_version(master_video['version_id'])
        extracted_metadata = cls._run_extracted_metadata(master=master)
        logging.debug(
            'Adding extracted metadata {0}'.format(extracted_metadata))
        deposit['_cds']['extracted_metadata'] = extracted_metadata
        record['_cds']['extracted_metadata'] = extracted_metadata

    @classmethod
    def _resolve_datacite_register(cls, record):
        """Register datacite."""
        logging.debug('Registering in DataCite')
        video_pid = PersistentIdentifier.query.filter_by(
            pid_type='recid', object_uuid=record.id,
            object_type='rec').one()
        datacite_register.apply(args=[video_pid.pid_value, str(record.id)])

    @classmethod
    def _resolve_cds(cls, record):
        """Build _cds."""
        logging.debug('Adding _cds field.')
        user_id = cls._resolve_user_id(email=record.pop('modified_by', None))
        record['_cds'] = {
            "state": {
                "file_transcode": "SUCCESS",
                "file_video_extract_frames": "SUCCESS",
                "file_video_metadata_extraction": "SUCCESS"
            },
            "modified_by": user_id,
        }

    @classmethod
    def _resolve_description(cls, record):
        """Build description."""
        if 'description' not in record:
            logging.debug('Adding empty description.')
            record['description'] = ''

    @classmethod
    def _resolve_publication_date(cls, record):
        """Build publication date."""
        if 'publication_date' not in record:
            logging.debug(
                'Record without publication date, adding creation date')
            record['publication_date'] = record.created.replace(
                tzinfo=None).strftime("%Y-%m-%d")
        record['date'] = record['publication_date']

    @classmethod
    def _resolve_license_copyright(cls, record):
        """Build license and copyright for video."""
        logging.debug('Verifying video license and copyright.')

        if 'copyright' not in record:
            logging.debug('Adding default CERN copyright.')
            record['copyright'] = {
                'holder': 'CERN',
                'year': str(record.created.year),
                'url': 'http://copyright.web.cern.ch',
            }
        if record['copyright']['holder'] == 'CERN' and not record[
                'copyright'].get('url') == 'http://copyright.web.cern.ch':
            record['copyright']['url'] = 'http://copyright.web.cern.ch'
            # video license

        if 'license' not in record:
            record['license'] = []
        without_general_license = all(
            [bool(l.get('material')) for l in record.get('license', [])])
        if record['license'] == [] or without_general_license:
            logging.debug('Adding default license.')
            holder = record['copyright']['holder']
            record['license'].append({
                'license': 'CERN' if holder == 'CERN' else 'unknown',
                'url': 'http://copyright.web.cern.ch'
                if holder == 'CERN' else '#',
            })

    @classmethod
    def _resolve_schema(cls, deposit, record):
        """Build bucket."""
        logging.debug('Setting correct schema.')
        if isinstance(record['$schema'], dict):
            record['$schema'] = record['$schema']['$ref']
        if Video.get_record_schema() == record['$schema']:
            deposit['$schema'] = current_jsonschemas.path_to_url(Video._schema)
        if Project.get_record_schema() == record['$schema']:
            deposit['$schema'] = current_jsonschemas.path_to_url(
                Project._schema)

    @classmethod
    def _resolve_bucket(cls, deposit, record):
        """Build bucket."""
        logging.debug('Creating new buckets, record and deposit.')
        bucket = Bucket.create(location=Location.get_by_name('videos'))
        deposit['_buckets'] = {'deposit': str(bucket.id)}
        RecordsBuckets.create(record=deposit.model, bucket=bucket)
        record['_buckets'] = deepcopy(deposit['_buckets'])
        db.session.commit()

    @classmethod
    def _resolve_deposit(cls, deposit, record):
        """Build _deposit."""
        logging.debug('Creating new deposit.')
        record_pid = PersistentIdentifier.query.filter_by(
            object_type='rec', object_uuid=record.id, pid_type='recid').one()
        deposit_pid = deposit_minter(record_uuid=deposit.id, data=deposit)
        userid = cls._resolve_user_id(
            email=record.get('_access', {}).get('update', [''])[0])
        deposit['_deposit'] = {
            'created_by': userid,
            'id': deposit_pid.pid_value,
            'owners': [userid],
            'pid': {
                # +1 because we update the record from the deposit
                'revision_id': record.revision_id + 1,
                'type': 'recid',
                'value': record_pid.pid_value,
            },
            'status': 'published'
        }
        record['_deposit'] = deepcopy(deposit['_deposit'])

    @classmethod
    def _resolve_files(cls, deposit, record):
        """Create files."""
        logging.info('Moving files from DFS.')
        # build deposit files
        bucket = as_bucket(deposit['_buckets']['deposit'])
        # build objects/tags from marc21 metadata
        for file_ in record.get('_files', []):
            cls._resolve_file(deposit=deposit, bucket=bucket, file_=file_)
        # attach the master tag to the proper dependent files
        cls._resolve_master_tag(deposit=deposit)
        if Video.get_record_schema() == record['$schema']:
            # probe metadata from video
            cls._resolve_extracted_metadata(deposit=deposit, record=record)
            # update tag 'timestamp'
            cls._update_timestamp(deposit=deposit)
        # build a partial files dump
        cls._resolve_dumps(record=deposit)
        # snapshot them to record bucket
        snapshot = bucket.snapshot(lock=True)
        db.session.add(RecordsBuckets(
            record_id=record.id, bucket_id=snapshot.id
        ))
        if Video.get_record_schema() == record['$schema']:
            # create an empty smil file
            cls._resolve_dumps(record=record)
            cls._resolve_smil(record=record)
            # update tag 'master'
            cls._update_tag_master(record=record)
            # create the full smil file
            cls._resolve_dumps(record=record)
            cls._resolve_smil(record=record)
            # create gif
            cls._create_gif(video=record)
            cls._create_gif(video=deposit)
            cls._resolve_dumps(record=record)

    @classmethod
    def _get_bucket(cls, record):
        """Resolve bucket."""
        records_buckets = RecordsBuckets.query.filter_by(
            record_id=record.id).one()
        return records_buckets.bucket

    @classmethod
    def _update_tag_master(cls, record):
        """Update tag master of files dependent from master."""
        bucket = cls._get_bucket(record=record)
        master_video = CDSVideosFilesIterator.get_master_video_file(record)
        for obj in ObjectVersion.get_by_bucket(bucket=bucket):
            if obj.get_tags()['context_type'] in cls.dependent_objs:
                ObjectVersionTag.create_or_update(
                    obj, 'master', master_video['version_id'])

    @classmethod
    def _resolve_smil(cls, record):
        """Build smil file."""
        logging.debug('Generating smil file.')
        bucket = cls._get_bucket(record=record)
        was_locked = bucket.locked
        bucket.locked = False
        master_video = CDSVideosFilesIterator.get_master_video_file(record)
        generate_smil_file(
            record['recid'], record,
            master_video['bucket_id'], master_video['version_id'],
            skip_schema_validation=True
        )
        bucket.locked = was_locked

    @classmethod
    def _resolve_dumps(cls, record):
        """Build files dump."""
        bucket = cls._get_bucket(record=record)
        files = []
        for o in ObjectVersion.get_by_bucket(bucket=bucket):
            # skip for dependent objs (like subformats)
            if o.get_tags()['context_type'] not in cls.dependent_objs:
                dump = {}
                dump_generic_object(obj=o, data=dump)
                if dump:
                    files.append(dump)
        record['_files'] = files

    @classmethod
    def _resolve_master_tag(cls, deposit):
        """Create the master tag for dependent files."""
        # build a partial files dump
        cls._resolve_dumps(record=deposit)
        # get master
        master_video = CDSVideosFilesIterator.get_master_video_file(deposit)
        # get deposit bucket
        bucket = cls._get_bucket(record=deposit)
        # attach the master tag
        for obj in ObjectVersion.get_by_bucket(bucket=bucket):
            if obj.get_tags()['context_type'] in cls.dependent_objs:
                ObjectVersionTag.create(
                    obj, 'master', master_video['version_id'])

    @classmethod
    def _get_migration_file_stream_and_size(cls, file_):
        """Build the full file path."""
        path = os.path.join(
            current_app.config['CDS_MIGRATION_RECORDS_BASEPATH'],
            file_['filepath'])
        return open(path, 'rb'), os.path.getsize(path)

    @classmethod
    def _resolve_file(cls, deposit, bucket, file_):
        """Resolve file."""
        def progress_callback(size, total):
            logging.debug('Moving file {0} of {1}'.format(total, size))

        # create object
        stream, size = cls._get_migration_file_stream_and_size(file_=file_)
        obj = ObjectVersion.create(
            bucket=bucket, key=file_['key'], stream=stream,
            size=size, progress_callback=progress_callback)
        # resolve preset info
        tags_to_guess_preset = file_.get('tags_to_guess_preset', {})
        if tags_to_guess_preset:
            file_['tags'].update(**cls._resolve_preset(
                obj=obj, clues=tags_to_guess_preset))
        tags_to_transform = file_.get('tags_to_transform', {})
        # resolve timestamp
        if 'timestamp' in tags_to_transform:
            file_['tags']['timestamp'] = tags_to_transform['timestamp']
        # create tags
        for key, value in file_.get('tags', {}).items():
            ObjectVersionTag.create(obj, key, value)

    @classmethod
    def _update_timestamp(cls, deposit):
        """Update timestamp from percentage to seconds."""
        logging.debug('Set correct timestamp for frames.')
        duration = float(deposit['_cds']['extracted_metadata']['duration'])
        bucket = CDSRecordDumpLoader._get_bucket(record=deposit)
        for obj in ObjectVersion.get_by_bucket(bucket=bucket):
            if 'timestamp' in obj.get_tags().keys():
                timestamp = duration * float(obj.get_tags()['timestamp']) / 100
                ObjectVersionTag.create_or_update(obj, 'timestamp', timestamp)

    @classmethod
    def _resolve_preset(cls, obj, clues):
        """Resolve preset."""
        logging.debug('Set correct preset names.')

        def guess_preset(preset_name, clues):
            presets = current_app.config['CDS_SORENSON_PRESETS']
            for ratio, subpreset in presets.items():
                for name, options in subpreset.items():
                    if preset_name == name and \
                            all([options.get(key) == value
                                 for key, value in clues.items()]):
                        return ratio, preset_name, options
            return None, None, None

        myclues = deepcopy(clues)
        preset = myclues.pop('preset', None)
        if preset:
            ratio, preset_quality, options = guess_preset(
                preset_name=preset, clues=myclues)
            if ratio:
                mypreset = deepcopy(options)
                mypreset['display_aspect_ratio'] = ratio
                mypreset['preset_quality'] = preset_quality
                return mypreset
        return {}

    @classmethod
    def _resolve_user_id(cls, email=None):
        """Resolve the owner id."""
        logging.debug('Set correct user id from email {0}.'.format(email))
        if not email:
            return -1
        return User.query.filter_by(email=email.lower()).one().id


class DryRunCDSRecordDumpLoader(CDSRecordDumpLoader):
    """Dry run."""

    @classmethod
    def _get_migration_file_stream_and_size(cls, file_):
        """Build the full file path."""
        from six import BytesIO
        return BytesIO(b'hello'), 5

    @classmethod
    def _run_extracted_metadata(cls, master):
        return dict(
            bit_rate='679886',
            duration='60.140000',
            size='5111048',
            avg_frame_rate='288000/12019',
            codec_name='h264',
            width='640',
            height='360',
            nb_frames='1440',
            display_aspect_ratio='16:9',
            color_range='tv',
        )
