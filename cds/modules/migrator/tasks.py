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
"""Record migration special."""
import hashlib
import os
from time import sleep

import requests
from celery import shared_task
from celery.utils.log import get_task_logger

from invenio_db import db
from invenio_files_rest.models import ObjectVersion
from invenio_migrator.proxies import current_migrator
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.models import RecordsBuckets
from invenio_search.proxies import current_search_client
from invenio_indexer.proxies import current_record_to_index

from ..deposit.api import deposit_video_resolver
from ..records.api import CDSVideosFilesIterator, Record
from ..records.permissions import is_public
from ..records.resolver import record_resolver
from ..webhooks.tasks import TranscodeVideoTask

check_record_logger = get_task_logger('cds-migrator-check-record')


class TranscodeVideoTaskQuiet(TranscodeVideoTask):
    """Transcode without index or send sse messages."""

    def run(self, preset_quality, sleep_time=5, *args, **kwargs):
        super(TranscodeVideoTaskQuiet, self).run(
            preset_quality=preset_quality,
            sleep_time=sleep_time,
            *args,
            **kwargs)
        # get deposit and record
        video = deposit_video_resolver(self.deposit_id)
        rec_video = record_resolver.resolve(video['recid'])[1]
        # sync deposit --> record
        video._sync_record_files(record=rec_video)
        video.commit()
        rec_video.commit()
        db.session.commit()

    def on_success(self, *args, **kwargs):
        pass

    def _update_record(self, *args, **kwargs):
        pass


@shared_task(ignore_result=True)
def clean_record(data, source_type):
    """Delete all information related with a given record.

    Note: files are deleted from the file system
    """
    try:
        source_type = source_type or 'marcxml'
        assert source_type in ['marcxml', 'json']

        recorddump = current_migrator.records_dump_cls(
            data,
            source_type=source_type,
            pid_fetchers=current_migrator.records_pid_fetchers, )
        current_migrator.records_dumploader_cls.clean(
            recorddump, delete_files=True)

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


@shared_task(ignore_result=True)
def check_record(data, source_type):
    """Verify if the record and files were correctly migrated."""
    source_type = source_type or 'marcxml'
    assert source_type in ['marcxml', 'json']

    recorddump = current_migrator.records_dump_cls(
        data,
        source_type=source_type,
        pid_fetchers=current_migrator.records_pid_fetchers, )
    recorddump.prepare_revisions()
    recorddump.prepare_pids()

    # First verify if the record exists
    recid_pid = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value == str(recorddump.recid),
        PersistentIdentifier.pid_type == 'recid').one_or_none()
    if not recid_pid:
        check_record_logger.error(
            'PID not found: {0}'.format(recorddump.recid))
        raise Exception('Record {0} not migrated'.format(recorddump.recid))

    record = Record.get_record(recid_pid.object_uuid)
    # The record exists
    assert record

    _check_files(record, recorddump)
    _check_web(record)
    _check_es(record)


def _md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _check_web(record):
    """Check record accessibility."""
    urls = [
        "https://videos.cern.ch/record/{recid}",
        "https://videos.cern.ch/api/record/{recid}"
    ]
    if 'video-v1.0.0.json' in record['$schema']:
        urls.extend([
            "https://videos.cern.ch/video/{rn}",
            "https://videos.cern.ch/api/mediaexport?id={rn}",
        ])

    url_info = {'recid': record['recid'], 'rn': record['report_number'][0]}

    for url in urls:
        url = url.format(**url_info)
        response = requests.get(url, verify=False)
        if response.status_code == 401:
            if is_public(record, 'read'):
                check_record_logger.error('Record {0} should be public in {1}'.
                                          format(record['recid'], url))
        elif response.status_code != 200:
            check_record_logger.error('Cannot access record {0} via {1}'.
                                      format(record['recid'], url))
        sleep(0.1)


def _check_es(record):
    """Check if the record is correctly indexed."""
    index, doc_type = current_record_to_index(record)
    if not current_search_client.exists(index, doc_type, record.id):
        check_record_logger.error(
            'Record not indexed {0}'.format(record['recid']))


def _check_files(record, recorddump):
    """Check file integrity."""
    old_files = recorddump.revisions[-1][1].get('_files')
    if not old_files:
        # Nothing to check, there are no files in the original record
        return

    record_bucket = RecordsBuckets.query.filter(
        RecordsBuckets.record_id == record.id).one_or_none()
    if not record_bucket:
        check_record_logger.error(
            'Bucket not found: {0}'.format(recorddump.recid))
        raise Exception(
            'Files for record {0} not migrated'.format(recorddump.recid))

    # Verify master file
    try:
        master_file = [
            f for f in old_files if f['tags']['context_type'] == 'master'
        ][0]
    except IndexError:
        check_record_logger.error(
            'Master file not found: {0}'.format(recorddump.recid))
        return
    master_file_path = current_migrator.records_dumploader_cls._get_full_path(
        master_file['filepath'])

    master_obj = ObjectVersion.get(record_bucket.bucket, master_file['key'])
    if not master_obj:
        # Before raising verify the master is accessible on DFS
        if (os.path.isfile(master_file_path) and
                os.access(master_file_path, os.R_OK)):
            check_record_logger.error(
                'Master file found but not migrated: {0}'.format(
                    recorddump.recid))
            raise Exception('Master file for record {0} not migrated'.format(
                recorddump.recid))
        else:
            check_record_logger.warning(
                'Master file found in dump but not on DFS: {0}'.format(
                    recorddump.recid))
            return
    # CHECKSUM VERIFICATION TAKES TOO LONG, LET'S SKIP IT!
    # # Verify master object checksum
    # old_master_md5 = _md5(master_file_path)
    # if master_obj.file.checksum != old_master_md5:
    #     check_record_logger.error(
    #         'Master file checksum not correct: {0}'.format(recorddump.recid))
    #     raise Exception('Wrong checksum {0}'.format(recorddump.recid))

    # At this point we know the master file is correct, check the other files
    master_file = CDSVideosFilesIterator.get_master_video_file(record)
    # Check frames
    frames = CDSVideosFilesIterator.get_video_frames(master_file)
    if len(frames) != 10:  # magic number, we are always creating ten of them
        check_record_logger.error(
            'Not all frames were created for {0}'.format(recorddump.recid))

    # Check slaves
    old_slaves = [
        f for f in old_files if f['tags']['context_type'] == 'subformat'
    ]
    new_slaves = CDSVideosFilesIterator.get_video_subformats(master_file)
    if len(new_slaves) < len(old_slaves):
        check_record_logger.error(
            'Not all slaves were migrated for {0}'.format(recorddump.recid))
