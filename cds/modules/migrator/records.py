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
from cds_sorenson.api import get_all_distinct_qualities
from celery.utils.log import get_task_logger
from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from invenio_deposit.minters import deposit_minter
from invenio_files_rest.models import (Bucket, BucketTag, FileInstance,
                                       Location, ObjectVersion,
                                       ObjectVersionTag, as_bucket,
                                       as_object_version)
from invenio_files_rest.tasks import remove_file_data
from invenio_jsonschemas import current_jsonschemas
from invenio_migrator.records import RecordDump, RecordDumpLoader
from invenio_migrator.tasks.records import import_record
from invenio_pidstore.models import PersistentIdentifier, RecordIdentifier
from invenio_records.models import RecordMetadata
from invenio_records_files.api import Record
from invenio_records_files.models import RecordsBuckets
from sqlalchemy.orm.exc import NoResultFound

from ..deposit.api import Project, Video, record_unbuild_url
from ..deposit.tasks import datacite_register
from ..records.api import CDSVideosFilesIterator, dump_generic_object
from ..records.fetchers import report_number_fetcher
from ..records.minters import doi_minter
from ..records.serializers.smil import generate_smil_file
from ..records.tasks import create_symlinks
from ..records.validators import PartialDraft4Validator
from ..webhooks.tasks import ExtractFramesTask, ExtractMetadataTask
from .tasks import TranscodeVideoTaskQuiet
from .utils import (cern_movie_to_video_pid_fetcher, process_fireroles,
                    update_access)

logger = get_task_logger(import_record.__name__)


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
            report_number_fetcher,
            cern_movie_to_video_pid_fetcher,
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
            doi_minter(record_uuid=record.id, data=record)
            cls._resolve_project_id(video=record)
        cls._resolve_cds(record=record)

        record.commit()
        db.session.commit()

        if Video.get_record_schema() == record['$schema']['$ref']:
            cls._resolve_datacite_register(record=record)
        record, deposit = cls._create_deposit(record=record)

        # commit!
        deposit.commit()
        record.commit()
        db.session.commit()

        if Video.get_record_schema() == record['$schema']:
            cls._create_missing_subformats(record=record, deposit=deposit)

        cls._create_symlinks(record=record)
        return record

    @classmethod
    def clean(cls, dump, delete_files=False):
        """Clean a record with all connected objects."""
        logging.debug('Clean record {0}'.format(dump.recid))
        record = dump.resolver.resolve(dump.data['recid'])[1]
        record_uuid = record.id
        deposit = cls._get_deposit(record)
        if deposit:
            # clean deposit
            cls.clean_record(deposit.id)
        cls.clean_record(record_uuid, recid=dump.data['recid'])

    @classmethod
    def _get_deposit(cls, record):
        """Get deposit."""
        logging.debug('Get deposit for record {0}'.format(record.id))
        records = RecordMetadata.query.all()
        #  records = RecordMetadata.query.filter([
        #      sqlalchemy.cast(
        #          RecordMetadata.json['recid'],
        #          sqlalchemy.Integer) == sqlalchemy.type_coerce(
        #              int(record['recid']), sqlalchemy.JSON)
        #  ]).all()
        for record_db in records:
            try:
                if record['recid'] == record_db.json['recid']:
                    pid = PersistentIdentifier.query.filter_by(
                        pid_type='depid', object_uuid=str(record_db.id)).one()
                    return Record.get_record(pid.object_uuid)
            except Exception:
                pass
        logging.debug('Clean deposit, deposit for the record '
                      '{0} not found'.format(record.id))
        return None

    @classmethod
    def clean_record(cls, uuid, recid=None):
        """Clean record."""
        logging.debug('Clean record {1}:{0}'.format(uuid, recid or 'deposit'))
        record_bucket = RecordsBuckets.query.filter(
            RecordsBuckets.record_id == uuid).one_or_none()
        PersistentIdentifier.query.filter(
            PersistentIdentifier.object_uuid == uuid).delete()
        RecordsBuckets.query.filter(RecordsBuckets.record_id == uuid).delete()
        RecordMetadata.query.filter(RecordMetadata.id == uuid).delete()

        if recid:
            RecordIdentifier.query.filter(
                RecordIdentifier.recid == recid).delete()

        files = []
        if record_bucket:
            bucket = as_bucket(record_bucket.bucket_id)
            record_bucket.bucket.locked = False
            # Make files writable
            for obj in bucket.objects:
                files.append(obj.file.id)
                obj.file.writable = True
                db.session.add(obj.file)
            bucket.remove()
        db.session.commit()
        cls.clean_files(files)

    @classmethod
    def clean_files(cls, file_ids):
        """Clean files."""
        logging.debug('Clean files: {0}'.format(file_ids))
        for file_id in file_ids:
            remove_file_data.s(file_id).apply()

    @classmethod
    def _get_frames(cls, master_video):
        """Get Frames."""
        return [FileInstance.get(f['file_id']).uri
                for f in CDSVideosFilesIterator.get_video_frames(
                    master_file=master_video)]

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
        frames = cls._get_frames(master_video=master_video)
        logging.debug(
            'Create gif for {0} using {1}'.format(str(video.id), frames))
        # create GIF
        output_folder = tempfile.mkdtemp()
        ExtractFramesTask._create_gif(bucket=str(bucket.id), frames=frames,
                                      output_dir=output_folder,
                                      master_id=master_video['version_id'])
        shutil.rmtree(output_folder)
        # lock bucket
        bucket.locked = was_locked
        db.session.merge(bucket)

    @classmethod
    def _create_symlinks(cls, record):
        """Create symlinks."""
        logging.debug('Schedule tasks to create symlinks.')
        # create file symlinks delayed (waiting the commit)
        create_symlinks.s(
            previous_record=record, record_uuid=str(record.id)
        ).apply_async(countdown=90)

    @classmethod
    def _resolve_project_id(cls, video):
        """Resolve project id."""
        try:
            video['_project_id'] = record_unbuild_url(video['_project_id'])
        except KeyError:
            # The video doesn't have projet
            logging.error(
                '#MISSING_PROJECT for record {0}'.format(video['recid']))

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
        # TODO: fix duration

    @classmethod
    def _resolve_datacite_register(cls, record):
        """Register datacite."""
        logging.debug('Registering in DataCite')
        video_pid = PersistentIdentifier.query.filter_by(
            pid_type='recid', object_uuid=record.id,
            object_type='rec').one()
        datacite_register.s(video_pid.pid_value, str(record.id)).apply_async()

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
        # Projects only have publication date
        if Video.get_record_schema() == record['$schema']:
            record.setdefault('date', record['publication_date'])

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
    def _clean_file_list(cls, record):
        """Remove unreachable files from the list (on DFS)."""
        logging.info('Cleaning file list.')
        new_file_list = []
        for f in record.get('_files', []):
            path = cls._get_full_path(filepath=f['filepath'])
            # No XRootD, accesing DFS
            if os.path.isfile(path):
                new_file_list.append(f)
            else:
                logging.error('#FILE_ERROR cannot open {0}'.format(f))
            record['_files'] = new_file_list

    @classmethod
    def _resolve_files(cls, deposit, record):
        """Create files."""
        cls._clean_file_list(record)
        logging.info('Moving files from DFS.')
        bucket = as_bucket(deposit['_buckets']['deposit'])
        if Video.get_record_schema() == record['$schema']:
            master = cls._resolve_master_file(record, bucket)
            if master:
                cls._create_or_update_frames(record=record, master_file=master)
                # build objects/tags from marc21 metadata
                for file_ in record.get('_files', []):
                    if file_['tags']['context_type'] != 'master':
                        cls._resolve_file(bucket=bucket, file_=file_)
                # attach the master tag to the proper dependent files
                cls._resolve_master_tag(deposit=deposit)
                # probe metadata from video
                cls._resolve_extracted_metadata(deposit=deposit, record=record)
                # update tag 'timestamp'
                cls._update_timestamp(deposit=deposit)
                # build a partial files dump
                cls._resolve_dumps(record=deposit)
                # create gif
                cls._create_gif(video=deposit)
        cls._resolve_dumps(record=deposit)
        # snapshot them to record bucket
        snapshot = bucket.snapshot(lock=True)
        db.session.add(RecordsBuckets(
            record_id=record.id, bucket_id=snapshot.id
        ))
        cls._resolve_dumps(record=record)
        if Video.get_record_schema() == record['$schema'] and master:
            # update tag 'master'
            cls._update_tag_master(record=record)
            # create an empty smil file
            cls._resolve_smil(record=record)
            # create the full smil file
            cls._resolve_dumps(record=record)
            cls._resolve_smil(record=record)

    @classmethod
    def _clean_file(cls, frame):
        """Clean object and file."""
        obj = ObjectVersion.query.filter_by(
            version_id=frame['version_id']).one()
        ObjectVersion.delete(bucket=obj.bucket, key=obj.key)

    @classmethod
    def _get_minimum_frames(cls):
        """Get minimum frames."""
        return 10

    @classmethod
    def _get_frames_info(cls, record):
        """Get frames info."""
        # get master
        master_video = CDSVideosFilesIterator.get_master_video_file(record)
        # get frames
        return (master_video,
                [f for f in CDSVideosFilesIterator.get_video_frames(
                    master_file=master_video)])

    @classmethod
    def _create_or_update_frames(cls, record, master_file):
        """Check and rebuild frames if needed."""
        files = record.get('_files', [])
        filtered = [f for f in files
                    if f['tags']['media_type'] != 'image'
                    or f['tags']['context_type'] != 'frame']
        if len(files) - len(filtered) < cls._get_minimum_frames():
            # filter frames if there are
            record['_files'] = filtered
            # create frames and add them inside the record
            record['_files'] = record['_files'] + cls._create_frame(
                object_=as_object_version(master_file))

    @classmethod
    def _create_frame(cls, object_):
        """Create a temporary frame to migrate."""
        # get metadata from the master file
        metadata = ExtractMetadataTask.get_metadata_tags(
            object_=object_)
        # get time informations
        options = ExtractFramesTask._time_position(
            duration=metadata['duration'])
        # recreate frames
        output_folder = tempfile.mkdtemp()
        frames = ExtractFramesTask._create_tmp_frames(object_=object_,
                                                      output_dir=output_folder,
                                                      **options)
        return [
            dict(filepath=f,
                 key=os.path.basename(f).split('.')[0],
                 tags={'content_type': 'jpg',
                       'context_type': 'frame',
                       'media_type': 'image'},
                 tags_to_transform={'timestamp': ((i+1)*10)-5})
            for i, f in enumerate(frames)]

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
    def _get_full_path(cls, filepath):
        """Get full path."""
        # No XRootD, accesing DFS
        return os.path.join(
            current_app.config['CDS_MIGRATION_RECORDS_BASEPATH'],
            filepath)

    @classmethod
    def _get_migration_file_stream_and_size(cls, file_):
        """Build the full file path."""
        # No XRootD, accesing DFS
        path = cls._get_full_path(filepath=file_['filepath'])
        return open(path, 'rb'), os.path.getsize(path)

    @classmethod
    def _resolve_master_file(cls, record, bucket):
        """Resolve a given context type file type."""
        try:
            [master_video] = [f for f in record['_files']
                              if f['tags']['context_type'] == 'master']
            return cls._resolve_file(bucket=bucket, file_=master_video)
        except Exception as e:
            # Either the file doesn't exist or can't be read.
            logging.error('#MASTER_FILE_ERROR {0}'.format(e))
            return None

    @classmethod
    def _resolve_file(cls, bucket, file_):
        """Resolve file."""
        def progress_callback(size, total):
            logging.debug('Moving file {0} of {1}'.format(total, size))

        # resolve preset info
        tags_to_guess_preset = file_.get('tags_to_guess_preset', {})
        if tags_to_guess_preset:
            file_['tags'].update(**cls._resolve_preset(
                obj=None, clues=tags_to_guess_preset))
            # we cannot deal with it now delete the file
            if 'preset_quality' not in file_['tags']:
                return None
        # create object
        stream, size = cls._get_migration_file_stream_and_size(file_=file_)
        obj = ObjectVersion.create(
            bucket=bucket, key=file_['key'], stream=stream,
            size=size, progress_callback=progress_callback)
        tags_to_transform = file_.get('tags_to_transform', {})
        # resolve timestamp
        if 'timestamp' in tags_to_transform:
            file_['tags']['timestamp'] = tags_to_transform['timestamp']
        # Add DFS path to run ffmpeg without copying the file
        file_['tags']['dfs_path'] = cls._get_full_path(
            filepath=file_['filepath'])
        # create tags
        for key, value in file_.get('tags', {}).items():
            ObjectVersionTag.create(obj, key, value)

        db.session.commit()
        return obj.version_id

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
                # copy preset informations
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
        try:
            return User.query.filter_by(email=email.lower()).one().id
        except NoResultFound:
            logging.error('Email not found {0}'.format(email))
            # cds.support@cern.ch user id
            return 1257250

    @classmethod
    def _create_missing_subformats(cls, record, deposit):
        """Create missing subformats."""
        # get master
        master = CDSVideosFilesIterator.get_master_video_file(deposit)
        if not master:
            return

        ratio = master['tags']['display_aspect_ratio']
        max_width = int(master['tags']['width'])
        max_height = int(master['tags']['height'])

        assert ratio in current_app.config['CDS_SORENSON_PRESETS']
        preset = current_app.config['CDS_SORENSON_PRESETS'][ratio]

        # get required presets
        prq = [key for (key, value) in preset.items()
               if value['width'] <= max_width or value['height'] <= max_height]
        try:
            # get subformat preset qualities
            pqs = [form['tags']['preset_quality'] for form in master['subformat']]
        except KeyError:
            pqs = []
        # find missing subformats
        missing = set(prq) - set(pqs)

        # run tasks for missing
        for miss in missing:
            TranscodeVideoTaskQuiet().s(
                version_id=master['version_id'], preset_quality=miss,
                deposit_id=deposit['_deposit']['id']
            ).apply_async()

        # return the missing subformats labels, if any
        return missing


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
