# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017, 2018 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.
"""Records tasks."""

from __future__ import absolute_import, print_function

import json
from datetime import datetime, timedelta
import requests
import sqlalchemy as sa
from cds.modules.ffmpeg import ff_probe_all
from cds.modules.records.api import CDSVideosFilesIterator
from cds.modules.records.utils import format_pid_link, is_deposit, is_record
from cds_sorenson.api import can_be_transcoded, get_all_distinct_qualities
from celery import shared_task
from flask import current_app
from flask_mail import Message
from invenio_cache import current_cache
from invenio_db import db
from invenio_files_rest.models import Bucket, FileInstance, as_object_version
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.models import RecordMetadata
from invenio_records_files.api import ObjectVersion
from invenio_records_files.models import RecordsBuckets
from requests.exceptions import RequestException

from .api import CDSRecord, Keyword
from .search import KeywordSearch, query_to_objects

# from .symlinks import SymlinksCreator


def _get_keywords_from_api(url):
    """Get keywords list from API."""
    request = requests.get(
        url, headers={
            'User-Agent': current_app.config.get('RECORDS_ID_PROVIDER_AGENT')
        }).text

    keywords = {}
    for tag in json.loads(request)['tags']:
        keywords[tag['id']] = dict(name=tag['name'], provenance=url)
    return keywords


def _update_existing_keywords(indexer, keywords_api, keywords_db):
    """Update existing keywords."""

    def _keyword_data(values):
        """Prepare the keyword data."""
        return dict(
            name=values.get('name'),
            provenance=values.get('provenance', ''),
            deleted=values.get('deleted', False))

    def _check_if_updated(old_keyword, new_data):
        """Return True in the keyword should be updated."""
        old_data = _keyword_data(old_keyword)
        return old_data != new_data

    to_db = []
    to_update_index = []
    keywords_saved = {k['key_id']: k for k in keywords_db}
    keys_saved = keywords_saved.keys()
    # check loaded keywords against the keywords in the database
    for key_id, values in keywords_api.items():
        keyword = None

        if key_id not in keys_saved:
            # create a new keyword
            data = _keyword_data(values)
            data.update(key_id=key_id)
            keyword = Keyword.create(data=data)
        elif _check_if_updated(keywords_saved[key_id], _keyword_data(values)):
            # update a keyword (also handles the restoring of a keyword)
            keywords_saved[key_id].update(_keyword_data(values))
            keyword = keywords_saved[key_id]

        if keyword:
            to_db.append(keyword)

    for keyword in to_db:
        keyword = keyword.commit()
        to_update_index.append(str(keyword.id))

    indexer.bulk_index(iter(to_update_index))


def _delete_not_existing_keywords(indexer, keywords_api, keywords_db):
    """Delete not existing keywords."""
    to_soft_delete = []
    keys_loaded = keywords_api.keys()
    # check if some keywords is deleted
    for keyword in keywords_db:
        if keyword['deleted'] is False and \
                keyword['key_id'] not in keys_loaded:
            # soft delete the key_id
            keyword['deleted'] = True
            keyword.commit()
            to_soft_delete.append(str(keyword.id))

    indexer.bulk_index(iter(to_soft_delete))


def _send_email(subject, body, sender, recipients):
    current_app.extensions['mail'].send(
        Message(subject, sender=sender, recipients=recipients, body=body))


def _get_all_records_with_bucket():
    """Get query for all registered records with a bucket."""
    return RecordMetadata.query \
        .join(PersistentIdentifier,
              PersistentIdentifier.object_uuid == RecordMetadata.id) \
        .join(RecordsBuckets) \
        .join(Bucket) \
        .join(ObjectVersion) \
        .filter(
            PersistentIdentifier.status == PIDStatus.REGISTERED,
            PersistentIdentifier.pid_type == 'recid')


def _filter_by_last_created(query, start_date, end_date=None):
    """Return records UUIDs filtered by ObjectVersion creation interval."""
    if start_date and end_date:
        query = query \
            .filter(ObjectVersion.created >= start_date,
                    ObjectVersion.created <= end_date)
    else:
        query = query \
            .filter(ObjectVersion.created >= start_date)

    return query \
        .group_by(RecordMetadata.id) \
        .with_entities(RecordMetadata.id)


@shared_task(bind=True)
def keywords_harvesting(self, max_retries=5, countdown=5):
    """Harvest all keywords."""
    try:
        # load from remote API the up-to-date list of keywords
        keywords_api = _get_keywords_from_api(
            url=current_app.config['CDS_KEYWORDS_HARVESTER_URL'])

        # load the list of keywords in the database
        keywords_db = query_to_objects(
            query=KeywordSearch().params(version=True), cls=Keyword)

        # index lists
        indexer = RecordIndexer()

        _update_existing_keywords(
            indexer=indexer,
            keywords_api=keywords_api,
            keywords_db=keywords_db)
        _delete_not_existing_keywords(
            indexer=indexer,
            keywords_api=keywords_api,
            keywords_db=keywords_db)

        db.session.commit()
    except RequestException as exc:
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=exc)


@shared_task(ignore_result=True, default_retry_delay=10 * 60)
def create_symlinks(previous_record, record_uuid):
    """Create video symlinks."""
    # FIXME: couldn't find a way to create symlinks with xrootd
    # record_new = CDSRecord.get_record(record_uuid)
    # SymlinksCreator().create(previous_record, record_new)


def format_file_integrity_report(report):
    """Format the email body for the file integrity report."""
    lines = []
    for entry in report:
        f = entry['file']
        lines.append('ID: {}'.format(str(f.id)))
        lines.append('URI: {}'.format(f.uri))
        lines.append('Name: {}'.format(entry.get('filename')))
        lines.append('Created: {}'.format(f.created))
        lines.append('Checksum: {}'.format(f.checksum))
        lines.append('Last Check: {}'.format(f.last_check_at))
        if 'record' in entry:
            lines.append(u'Record: {}'.format(
                format_pid_link(current_app.config['RECORDS_UI_ENDPOINT'],
                                entry['record'].get('recid'))))
        if 'deposit' in entry:
            lines.append(u'Deposit: {}'.format(
                format_pid_link(
                    current_app.config['DEPOSIT_UI_ENDPOINT_DEFAULT'],
                    entry['deposit'].get('_deposit', {}).get('id'))))
        lines.append(('-' * 80) + '\n')
    return '\n'.join(lines)


@shared_task
def file_integrity_report():
    """Send a report of uhealthy/missing files to CDS admins."""
    # First retry verifying files that errored during their last check
    files = FileInstance.query.filter(FileInstance.last_check.is_(None))
    for f in files:
        try:
            f.clear_last_check()
            db.session.commit()
            f.verify_checksum(throws=False)
            db.session.commit()
        except Exception:
            pass  # Don't fail sending the report in case of some file error

    report = []
    unhealthy_files = (FileInstance.query.filter(
        sa.or_(
            FileInstance.last_check.is_(None),
            FileInstance.last_check.is_(False))).order_by(
                FileInstance.created.desc()))

    for f in unhealthy_files:
        entry = {'file': f}
        for o in f.objects:
            entry['filename'] = o.key
            # Find records/deposits for the files
            rb = RecordsBuckets.query.filter(
                RecordsBuckets.bucket_id == o.bucket_id).one_or_none()
            if rb and rb.record and rb.record.json:
                if is_deposit(rb.record.json):
                    entry['deposit'] = rb.record.json
                elif is_record(rb.record.json):
                    entry['record'] = rb.record.json
        report.append(entry)

    if report:
        # Format and send the email
        subject = u'[CDS Videos] Files integrity report [{}]'.format(
            datetime.now())
        body = format_file_integrity_report(report)
        sender = current_app.config['NOREPLY_EMAIL']
        recipients = [current_app.config['CDS_ADMIN_EMAIL']]
        _send_email(subject, body, sender, recipients)


@shared_task
def subformats_integrity_report(start_date=None, end_date=None):
    """Send a report of all corrupted subformats to CDS admins."""
    report = []

    def _probe_video_file(obj, record):
        """Run ffmpeg on a video file"""
        try:
            # Expecting the storage to be mounted on the machine
            probe = ff_probe_all(obj.file.uri.replace(
                current_app.config['VIDEOS_XROOTD_ENDPOINT'], ''))

            if not probe.get('streams'):
                report.append({
                    'message': 'No video streams',
                    'recid': record['recid'],
                    'report_number': record['report_number'][0],
                    'other': obj})

        except Exception as e:
            report.append({
                'message': 'Error while running ff_probe_all',
                'recid': record['recid'],
                'report_number': record['report_number'][0],
                'other': obj,
                'error': repr(e)})

    def _format_report(report):
        """Format the email body for the file integrity report."""
        lines = []
        for entry in report:
            lines.append('Message: {}'.format(entry.get('message')))
            lines.append(u'Record: {}'.format(
                    format_pid_link(current_app.config['RECORDS_UI_ENDPOINT'],
                                    entry.get('recid'))))
            lines.append('Report number: {}'.format(
                entry.get('report_number')))

            if entry.get('other'):
                lines.append('File name: {}'.format(entry.get('other').key))
                lines.append('File id: {}'.format(entry.get('other').file_id))
                lines.append('Version id: {}'.format(
                    entry.get('other').bucket_id))
                lines.append('Bucket id: {}'.format(
                    entry.get('other').version_id))
            lines.append('Error message: {}'.format(entry.get('error')))
            lines.append(('-' * 80) + '\n')

        return '\n'.join(lines)

    cache = current_cache.get('task_subformats_integrity:details') or {}
    if 'last_run' not in cache:
        # Save the last week date to have a default value the first time
        cache['last_run'] = datetime.utcnow() - timedelta(days=7)

    query = _filter_by_last_created(
        _get_all_records_with_bucket(),
        start_date or cache['last_run'],
        end_date)

    record_uuids = query \
        .group_by(RecordMetadata.id) \
        .with_entities(RecordMetadata.id)

    for record_uuid in record_uuids:
        record = CDSRecord.get_record(record_uuid.id)
        master = CDSVideosFilesIterator.get_master_video_file(record)

        if not master:
            report.append({
                'message': 'No master video found for the given record',
                'recid': record['recid'],
                'report_number': record['report_number'][0]})
            continue

        master_obj = as_object_version(master['version_id'])
        _probe_video_file(master_obj, record)

        subformats = CDSVideosFilesIterator.get_video_subformats(master)
        if not subformats:
            report.append({
                'message': 'No subformats found',
                'recid': record['recid']})
        for subformat in subformats:
            subformat_obj = as_object_version(subformat['version_id'])
            _probe_video_file(subformat_obj, record)

    cache['last_run'] = datetime.utcnow()
    current_cache.set('task_subformats_integrity:details', cache, timeout=-1)

    if report:
        # Format and send the email
        subject = u'[CDS Videos] Subformats integrity report [{}]'.format(
            datetime.now())
        body = _format_report(report)
        sender = current_app.config['NOREPLY_EMAIL']
        recipients = [current_app.config['CDS_ADMIN_EMAIL']]
        _send_email(subject, body, sender, recipients)


@shared_task
def missing_subformats_report(start_date=None, end_date=None):
    """Send a report of missing subformats to CDS admins."""
    report = []

    def _get_master_video(record):
        """Return master video."""
        master = CDSVideosFilesIterator.get_master_video_file(record)
        if not master:
            raise Exception("No master video found for the given record")

        return master, master['tags']['display_aspect_ratio'], \
            int(master['tags']['width']), int(master['tags']['height'])

    def _get_missing_subformats(subformats, ar, w, h):
        """Return missing and transcodable subformats."""
        dones = [subformat['tags']['preset_quality']
                 for subformat in subformats]
        missing = set(get_all_distinct_qualities()) - set(dones)
        transcodables = list(
            filter(lambda q: can_be_transcoded(q, ar, w, h), missing))
        return transcodables

    def _format_report(report):
        """Format the email body for the file integrity report."""
        lines = []
        for entry in report:
            lines.append('Message: {}'.format(entry.get('message')))
            lines.append(u'Record: {}'.format(
                    format_pid_link(current_app.config['RECORDS_UI_ENDPOINT'],
                                    entry.get('recid'))))
            lines.append('Report number: {}'.format(
                entry.get('report_number')))
            lines.append('Missing subformats: {}'.format(
                entry.get('missing_subformats')))
            lines.append(('-' * 80) + '\n')

        return '\n'.join(lines)

    cache = current_cache.get('task_missing_subformats:details') or {}
    if 'last_run' not in cache:
        # Save the last week date to have a default value the first time
        cache['last_run'] = datetime.utcnow() - timedelta(days=7)

    query = _filter_by_last_created(
                _get_all_records_with_bucket(),
                start_date or cache['last_run'],
                end_date)

    record_uuids = query \
        .group_by(RecordMetadata.id) \
        .with_entities(RecordMetadata.id)

    for record_uuid in record_uuids:
        record = CDSRecord.get_record(record_uuid.id)
        master, ar, w, h = _get_master_video(record)

        if not master:
            report.append({
                'message': 'No master video found for the given record',
                'recid': record.get('recid'),
                'report_number': record['report_number'][0]})
            continue

        # check missing subformats
        subformats = CDSVideosFilesIterator.get_video_subformats(master)
        missing = _get_missing_subformats(subformats, ar, w, h)
        if missing:
            report.append({
                'message': 'Missing subformats for the given record',
                'recid': record.get('recid'),
                'report_number': record['report_number'][0],
                'missing_subformats': missing})

        # check bucket ids consistency
        bucket_id = master['bucket_id']
        for f in subformats + \
                    CDSVideosFilesIterator.get_video_frames(master) + \
                    CDSVideosFilesIterator.get_video_subtitles(record):
            if f['bucket_id'] != bucket_id:
                report.append({
                    'message': 'Different buckets in the same record',
                    'recid': record.get('recid'),
                    'report_number': record['report_number'][0],
                    'buckets': 'Master: {0} - {1}: {2}'.format(bucket_id,
                                                               f['key'],
                                                               f['bucket_id'])
                })

    cache['last_run'] = datetime.utcnow()
    current_cache.set('task_missing_subformats:details', cache, timeout=-1)

    if report:
        # Format and send the email
        subject = u'[CDS Videos] Missing subformats report [{}]'.format(
            datetime.now())
        body = _format_report(report)
        sender = current_app.config['NOREPLY_EMAIL']
        recipients = [current_app.config['CDS_ADMIN_EMAIL']]
        _send_email(subject, body, sender, recipients)
