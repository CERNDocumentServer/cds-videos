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

from os.path import splitext

import arrow
from copy import deepcopy
from flask import current_app

from cds_dojson.marc21 import marc21
from cds_dojson.marc21.utils import create_record
from invenio_accounts.models import User
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_files_rest.models import Bucket, BucketTag, Location
from invenio_migrator.records import RecordDump, RecordDumpLoader
from invenio_records.api import Record
from invenio_records_files.models import RecordsBuckets
from invenio_jsonschemas import current_jsonschemas
from invenio_deposit.minters import deposit_minter

from .utils import process_fireroles, update_access
from ..records.fetchers import report_number_fetcher
from ..records.minters import _doi_minter
from ..deposit.api import Project, Video, record_build_url, record_unbuild_url
from ..deposit.tasks import datacite_register


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
            # FIXME how import the field 937__s (who made the modification)?
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

        for i in it:
            self.revisions.append(self._prepare_intermediate_revision(i))

        self.revisions.append(self._prepare_final_revision(it[-1]))


class CDSRecordDumpLoader(RecordDumpLoader):
    """Migrate a CDS record."""

    @classmethod
    def create(cls, dump):
        """Update an existing record."""
        record = super(CDSRecordDumpLoader, cls).create(dump=dump)
        cls._resolve_publication_date(record=record)
        if Video.get_record_schema() == record['$schema']['$ref']:
            cls._resolve_license_copyright(record=record)
            cls._resolve_description(record=record)
            _doi_minter(record_uuid=record.id, data=record)
            cls._resolve_project(record)
        cls._resolve_cds(record=record)

        record.commit()
        db.session.commit()

        if Video.get_record_schema() == record['$schema']['$ref']:
            cls._resolve_datacite_register(record=record)
        return record

    @classmethod
    def _create_deposit(cls, record):
        """Create a deposit from the record."""
        data = deepcopy(record)
        deposit = Record.create(data)
        cls._resolve_schema(deposit=deposit, record=record)
        cls._resolve_deposit(deposit=deposit, record=record)
        cls._resolve_bucket(deposit=deposit, record=record)
        # commit!
        deposit.commit()
        record.commit()
        db.session.commit()
        return deposit

    @classmethod
    def _resolve_datacite_register(cls, record):
        """Register datacite."""
        video_pid = PersistentIdentifier.query.filter_by(
            pid_type='recid', object_uuid=record.id,
            object_type='rec').one()
        datacite_register.delay(video_pid.pid_value, str(record.id))

    @classmethod
    def _resolve_cds(cls, record):
        """Build _cds."""
        record['_cds'] = {
            "state": {
                "file_transcode": "SUCCESS",
                "file_video_extract_frames": "SUCCESS",
                "file_video_metadata_extraction": "SUCCESS"
            },
            # FIXME remove it after migrate files!
            'extracted_metadata': {'duration': 12},
        }

    @classmethod
    def _resolve_description(cls, record):
        """Build description."""
        if 'description' not in record:
            record['description'] = ''

    @classmethod
    def _resolve_publication_date(cls, record):
        """Build publication date."""
        if 'publication_date' not in record:
            record['publication_date'] = record.created.replace(
                tzinfo=None).strftime("%Y-%m-%d")
        record['date'] = record['publication_date']

    @classmethod
    def _resolve_license_copyright(cls, record):
        """Build license and copyright for video."""
        if 'copyright' not in record:
            record['copyright'] = {
                'holder': 'CERN',
                'year': str(record.created.year),
                'url': 'http://copyright.web.cern.ch',
            }
        if record['copyright']['holder'] == 'CERN':
            record['copyright']['url'] = 'http://copyright.web.cern.ch'
            # video license
            if 'license' not in record:
                record['license'] = []
            without_general_license = all(
                [bool(l.get('material')) for l in record.get('license', [])])
            if record['license'] == [] or without_general_license:
                record['license'].append({
                    'license': 'CERN',
                    'url': 'http://copyright.web.cern.ch',
                })

    @classmethod
    def _resolve_schema(cls, deposit, record):
        """Build bucket."""
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
        bucket = Bucket.create(location=Location.get_by_name('videos'))
        deposit['_buckets'] = {'deposit': str(bucket.id)}
        RecordsBuckets.create(record=deposit.model, bucket=bucket)
        record['_buckets'] = deepcopy(deposit['_buckets'])

    @classmethod
    def _resolve_deposit(cls, deposit, record):
        """Build _deposit."""
        record_pid = PersistentIdentifier.query.filter_by(
            object_type='rec', object_uuid=record.id, pid_type='recid').one()
        deposit_pid = deposit_minter(record_uuid=deposit.id, data=deposit)
        userid = cls._resolve_owner(
            email=record.get('_access', {}).get('update', [''])[0])
        deposit['_deposit'] = {
            # FIXME
            'created_by': userid,
            'id': deposit_pid.pid_value,
            # FIXME
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
    def _resolve_owner(cls, email=None):
        """Resolve the owner id."""
        if not email:
            return -1
        return User.query.filter_by(email=email).one().id

    @classmethod
    def _resolve_project(cls, video):
        """Resolve project on video."""
        video_pid = PersistentIdentifier.query.filter_by(
            pid_type='recid', object_uuid=video.id, object_type='rec').one()
        video_rn = PersistentIdentifier.query.filter_by(
            pid_type='rn', object_uuid=video.id, object_type='rec').one()
        project_rn = video.get('_project_id')
        if project_rn:
            pid_rn = PersistentIdentifier.query.filter_by(
                pid_type='rn', pid_value=project_rn).first()
            if pid_rn:
                pid_rec = PersistentIdentifier.query.filter_by(
                    pid_type='recid', object_uuid=pid_rn.object_uuid,
                    object_type='rec').one()
                video['_project_id'] = pid_rec.pid_value
                project = Record.get_record(pid_rec.object_uuid)
                for index, ref in enumerate(project.get('videos', [])):
                    id_ = record_unbuild_url(ref['$ref'])
                    if id_ == video_rn.pid_value:
                        project['videos'][index][
                            '$ref'] = record_build_url(video_pid.pid_value)
                project.commit()

    @classmethod
    def create_files(cls, record, files, existing_files):
        """Create files.

        This method is currently limited to a single bucket per record.
        """
        default_bucket = None
        # Look for bucket id in existing files.
        for f in existing_files:
            if 'bucket' in f:
                default_bucket = f['bucket']
                break

        # Create a bucket in default location if none is found.
        if default_bucket is None:
            b = Bucket.create()
            BucketTag.create(b, 'record', str(record.id))
            default_bucket = str(b.id)
            db.session.commit()
        else:
            b = Bucket.get(default_bucket)

        record['_files'] = []
        for key, meta in files.items():
            obj = cls.create_file(b, key, meta)
            ext = splitext(obj.key)[1].lower()
            if ext.startswith('.'):
                ext = ext[1:]
            last_ver = meta[-1]
            rec_docs = [
                rec_doc[1] for rec_doc in last_ver['recids_doctype']
                if rec_doc[0] == last_ver['recid']
            ]

            record['_files'].append(
                dict(
                    bucket=str(obj.bucket.id),
                    key=obj.key,
                    version_id=str(obj.version_id),
                    size=obj.file.size,
                    checksum=obj.file.checksum,
                    type=ext,
                    doctype=rec_docs[0] if rec_docs else ''))
        db.session.add(RecordsBuckets(record_id=record.id, bucket_id=b.id))
        record.commit()
        db.session.commit()

        return [b]
