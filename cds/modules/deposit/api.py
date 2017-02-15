# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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

"""Deposit API."""

from __future__ import absolute_import, print_function

import os
import uuid

import datetime
import itertools
from contextlib import contextmanager
from os.path import splitext

import arrow
from celery import states
from cds.modules.records.minters import report_number_minter
from flask import current_app, url_for

from functools import wraps
from jsonschema.exceptions import ValidationError
from invenio_db import db
from invenio_deposit.api import Deposit, preserve, has_status
from invenio_files_rest.models import (Bucket, Location, MultipartObject,
                                       ObjectVersion, ObjectVersionTag)
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.validators import PartialDraft4Validator
from invenio_records_files.api import FileObject, FilesIterator
from invenio_records_files.models import RecordsBuckets
from invenio_records_files.utils import sorted_files_from_bucket
from invenio_sequencegenerator.api import Sequence
from sqlalchemy import func
from werkzeug.local import LocalProxy
from invenio_records.api import Record

from .errors import DiscardConflict
from ..webhooks.status import ComputeGlobalStatus, get_deposit_events, \
    iterate_events_results, get_tasks_status_by_task


PRESERVE_FIELDS = (
    '_deposit',
    '_buckets',
    '_files',
    'videos',
)

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def required(fields):
    """Check required fields."""
    def check(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            for field in fields:
                if field not in self:
                    raise ValidationError('{0} field not found'.format(field))
            return f(self, *args, **kwargs)
        return wrapper
    return check


class CDSFileObject(FileObject):
    """Wrapper for files."""

    @classmethod
    def _link(cls, bucket_id, key, _external=True):
        return url_for('invenio_files_rest.object_api',
                       bucket_id=bucket_id, key=key, _external=_external)

    def dumps(self):
        """Create a dump of the metadata associated to the record."""
        def _dumps(obj):
            tags = obj.get_tags()
            # File information
            content_type = splitext(obj.key)[1][1:].lower()
            context_type = tags.pop('context_type', '')
            media_type = tags.pop('media_type', '')
            return {
                'key': obj.key,
                'bucket_id': str(obj.bucket_id),
                'version_id': str(obj.version_id),
                'checksum': obj.file.checksum if obj.file else '',
                'size': obj.file.size if obj.file else 0,
                'file_id': str(obj.file_id),
                'completed': True,
                'progress': 100,
                'content_type': content_type,
                'context_type': context_type,
                'media_type': media_type,
                'tags': tags,
                'links': {
                    'self': (
                        current_app.config['DEPOSIT_FILES_API'] +
                        u'/{bucket}/{key}?versionId={version_id}'.format(
                            bucket=obj.bucket_id,
                            key=obj.key,
                            version_id=obj.version_id,
                        )),
                }
            }

        master_dump = _dumps(self.obj)
        # get all the slaves and add them inside <type> as a list order by key
        for slave in ObjectVersion.query.join(ObjectVersion.tags).filter(
                ObjectVersionTag.key == 'master',
                ObjectVersionTag.value == str(self.obj.version_id)
                ).order_by(func.length(ObjectVersion.key), ObjectVersion.key):
            master_dump.setdefault(
                slave.get_tags()['context_type'], []).append(_dumps(slave))
        # Sort slaves by key within their lists
        self.data.update(master_dump)

        return self.data


class CDSFilesIterator(FilesIterator):
    """Iterator for files."""

    def dumps(self, bucket=None):
        """Serialize files from a bucket."""
        files = []
        for o in sorted_files_from_bucket(bucket or self.bucket, self.keys):
            if 'master' in o.get_tags():
                continue
            dump = self.file_cls(o, self.filesmap.get(o.key, {})).dumps()
            if dump:
                files.append(dump)
        return files

    @staticmethod
    def get_master_video_file(record):
        """Get master video file from a Video record."""
        return next(
            f for f in record['_files']
            if f['media_type'] == 'video' and f['context_type'] == 'master')

    @staticmethod
    def get_video_subformats(master_file):
        return [video
                for video in master_file.get('subformat', [])
                if video['media_type'] == 'video' and video[
                    'context_type'] == 'subformat']

    @staticmethod
    def get_video_frames(master_file):
        return sorted(master_file.get('frame', []),
                      key=lambda s: s['tags']['timestamp'])


class CDSDeposit(Deposit):
    """Define API for changing deposit state."""

    sequence_name = None
    """Sequence identifier (`None` if not applicable)."""

    file_cls = CDSFileObject

    files_iter_cls = CDSFilesIterator

    def __init__(self, *args, **kwargs):
        """Init."""
        super(CDSDeposit, self).__init__(*args, **kwargs)
        self._update_tasks_status()
        self['_files'] = self._get_files_dump()

    @property
    def _bucket(self):
        """Get the bucket object."""
        records_buckets = RecordsBuckets.query.filter_by(
            record_id=self.id).first()
        if records_buckets:
            return records_buckets.bucket

    def _get_files_dump(self):
        """Get files without create the record_bucket."""
        bucket = self._bucket
        if bucket:
            return self.files_iter_cls(
                self, bucket=bucket,
                file_cls=self.file_cls).dumps()
        return []

    @classmethod
    def get_record(cls, id_, with_deleted=False):
        """Get record instance."""
        deposit = super(CDSDeposit, cls).get_record(
            id_=id_, with_deleted=with_deleted)
        #  deposit['_files'] = deposit._get_files_dump()
        return deposit

    @classmethod
    def get_records(cls, ids, with_deleted=False):
        """Get records."""
        deposits = super(CDSDeposit, cls).get_records(
            ids=ids, with_deleted=with_deleted)
        #  for deposit in deposits:
        #      deposit['_files'] = deposit._get_files_dump()
        return deposits

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a CDS deposit.

        Adds bucket creation immediately on deposit creation.
        """
        if '_deposit' not in data:
            id_ = id_ or uuid.uuid4()
            cls.deposit_minter(id_, data)
        bucket = Bucket.create(
            default_location=Location.get_default()
        )
        data['_buckets'] = {'deposit': str(bucket.id)}
        data['_deposit']['state'] = {}
        deposit = super(CDSDeposit, cls).create(
            data, id_=id_, validator=PartialDraft4Validator)
        RecordsBuckets.create(record=deposit.model, bucket=bucket)
        return deposit

    @property
    def multipart_files(self):
        """Get all multipart files."""
        return MultipartObject.query_by_bucket(self.files.bucket)

    @preserve(result=False, fields=PRESERVE_FIELDS)
    def clear(self, *args, **kwargs):
        """Clear only drafts."""
        super(CDSDeposit, self).clear(*args, **kwargs)

    @preserve(result=False, fields=PRESERVE_FIELDS)
    def update(self, *args, **kwargs):
        """Update only drafts."""
        super(CDSDeposit, self).update(*args, **kwargs)

    @preserve(result=False, fields=PRESERVE_FIELDS)
    def patch(self, *args, **kwargs):
        """Patch only drafts."""
        return super(CDSDeposit, self).patch(*args, **kwargs)

    @property
    def report_number(self):
        """Return report number."""
        try:
            return self['report_number']['report_number']
        except KeyError:
            return None

    @report_number.setter
    def report_number(self, value):
        """Set new report number."""
        self['report_number'] = dict(report_number=value)

    def _publish_new(self, id_=None):
        """Mint report number immediately before first publishing."""
        id_ = id_ or uuid.uuid4()
        self.mint_report_number(id_)
        return super(CDSDeposit, self)._publish_new(id_)

    def mint_report_number(self, id_, **kwargs):
        """Mint a new report number and update underlying record.

        .. note :
            Override in deposit subclass for custom behaviour.
        """
        if self.sequence_name:
            report_number_minter(id_, self, **kwargs)

    @has_status(status='published')
    def get_report_number_sequence(self, **kwargs):
        """Get the sequence generator of this Deposit class.

        .. note ::
            this should return a tuple, consisting of the sequence generator
            and the ``kwargs`` without the keywords used by this method
        """
        raise NotImplementedError()

    def commit(self, **kwargs):
        """Set partial validator as default."""
        if 'validator' not in kwargs:
            kwargs['validator'] = PartialDraft4Validator
        return super(CDSDeposit, self).commit(**kwargs)

    @classmethod
    def get_record_schema(cls):
        """Get record schema."""
        prefix = current_app.config['DEPOSIT_JSONSCHEMAS_PREFIX']
        schema = cls._schema[len(prefix):]
        return current_jsonschemas.path_to_url(schema)

    def dumps(self, **kwargs):
        """Return pure Python dictionary with record metadata."""
        self._update_tasks_status()
        data = super(CDSDeposit, self).dumps(**kwargs)
        return data

    def replace_refs(self):
        """Replace refs."""
        self._update_tasks_status()
        data = super(CDSDeposit, self).replace_refs()
        return data

    def _update_tasks_status(self):
        """Update tasks status."""
        if '_deposit' in self:
            self['_deposit']['state'] = self._current_tasks_status()

    def _current_tasks_status(self):
        """."""
        return {}

    @contextmanager
    def _process_files(self, record_id, data):
        """Snapshot bucket and add files in record during first publishing."""
        if self.files:
            assert not self.files.bucket.locked
            snapshot = self.files.bucket.snapshot()
            self.files.bucket.locked = True
            # dict of version_ids in original bucket to version_ids in
            # snapshot bucket for the each file
            old_to_new_version = {str(self.files[obj.key]['version_id']):
                                  str(obj.version_id)
                                  for obj in snapshot.objects
                                  if 'master' not in obj.get_tags()}
            # list of tags with 'master' key
            slave_tags = [tag for obj in snapshot.objects for tag in obj.tags
                          if tag.key == 'master']
            # change master of slave videos to new master object versions
            for tag in slave_tags:
                tag.value = old_to_new_version.get(tag.value)
            db.session.add_all(slave_tags)

            # Generate SMIL file
            data['_files'] = self.files.dumps(bucket=snapshot.id)

            from cds.modules.records.serializers.smil import generate_smil_file
            master_video = get_master_object(snapshot)
            if master_video:
                generate_smil_file(record_id, data, snapshot, master_video)

            # Update metadata with SMIL file information
            data['_files'] = self.files.dumps(bucket=snapshot.id)

            snapshot.locked = True

            yield data
            db.session.add(RecordsBuckets(
                record_id=record_id, bucket_id=snapshot.id
            ))
        else:
            yield

    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a deposit."""
        if 'publication_date' not in self:
            now = datetime.datetime.utcnow().date().isoformat()
            self['publication_date'] = now
        return super(CDSDeposit, self).publish(pid=pid, id_=id_, **kwargs)


def project_resolver(project_id):
    """Get records from PIDs."""
    pid = PersistentIdentifier.query.filter_by(
        pid_value=project_id
    ).one().object_uuid
    return Project.get_record(pid)


def cds_resolver(ids):
    """Get records from PIDs."""
    pids = [p.object_uuid for p in PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value.in_(ids)).all()]
    return CDSDeposit.get_records(pids)


def video_resolver(ids):
    """Get records from PIDs."""
    pids = [p.object_uuid for p in PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value.in_(ids)).all()]
    return Video.get_records(pids)


def video_build_url(video_id):
    """Build video url."""
    return url_for('invenio_deposit_rest.video_item', pid_value=video_id)


def record_build_url(video_id):
    """Build video url."""
    return url_for('invenio_records_rest.recid_item', pid_value=str(video_id))


def record_unbuild_url(url):
    """Extract the PID from the deposit/record url."""
    # TODO can we improve it?
    return os.path.basename(url)


def is_deposit(url):
    """Check if it's a deposit or a record."""
    # TODO can we improve check?
    return 'deposit' in url


def get_master_object(bucket):
    """Get master ObjectVersion from a bucket."""
    return ObjectVersion.get_by_bucket(bucket).join(
        ObjectVersionTag
    ).filter(
        ObjectVersionTag.key == 'preview',
        ObjectVersionTag.value == 'true'
    ).one_or_none()


class Project(CDSDeposit):
    """Define API for a project."""

    sequence_name = 'project-v1_0_0'
    """Sequence identifier."""

    _schema = 'deposits/records/project-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a project deposit.

        Adds bucket creation immediately on deposit creation.
        """
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        data.setdefault('videos', [])
        return super(Project, cls).create(data, id_=id_, **kwargs)

    @property
    def video_ids(self):
        """Get all video ids.

        .. note::

            If the video is published, it returns the recid.
            Otherwise, the ``video['_deposit']['id']``.

        :returns: A list of video ids.
        """
        return [record_unbuild_url(ref) for ref in self.video_refs]

    @property
    def video_refs(self):
        """Get all video refs.

        :returns: A list of video references.
        """
        return [video['$reference'] for video in self['videos']]

    def _find_refs(self, refs):
        """Find index of references."""
        result = {}
        for (key, value) in enumerate(self.video_refs):
            try:
                refs.index(value)
                result[key] = value
            except ValueError:
                pass
        return result

    def _update_videos(self, old_refs, new_refs):
        """Update metadata with new video references.

        :param old_refs: List contains the video references to substitute.
        :param new_refs: List contains the new video references
        """
        for (key, value) in enumerate(self.video_refs):
            try:
                index = old_refs.index(value)
                self['videos'][key] = {'$reference': new_refs[index]}
            except ValueError:
                pass

    def _delete_videos(self, refs):
        """Update metadata deleting videos.

        :param refs: List contains the video references to delete.
        """
        for index in self._find_refs(refs).keys():
            del self['videos'][index]

    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a project.

        The publishing involve the publication of all the videos inside.

        :returns: The new project version.
        """
        # get reference of all deposit still not published
        refs_old = [video_ref for video_ref in self.video_refs
                    if is_deposit(video_ref)]

        # extract the PIDs from them
        ids_old = [record_unbuild_url(video_ref) for video_ref in refs_old]

        # publish them and get the new PID
        refs_new = [record_build_url(video.publish().commit()['recid'])
                    for video in video_resolver(ids_old)]

        # update project video references
        self._update_videos(refs_old, refs_new)

        # Return project with generated report number
        self = Project(self.model.json, self.model)
        assert self.report_number

        # publish project
        return super(Project, self).publish(pid=pid, id_=id_, **kwargs)

    def discard(self, pid=None):
        """Discard project changes."""
        _, record = self.fetch_published()
        # if the list of videos is different return error
        if self['videos'] != record['videos']:
            raise DiscardConflict()
        # discard project
        return super(Project, self).discard(pid=pid)

    def _add_video(self, video):
        """Add a video."""
        video_ref = video.ref
        indices = self._find_refs([video_ref])
        if indices:
            # update video refs
            self['videos'][indices[video_ref]] = {'$reference': video_ref}
        else:
            # add new one
            self['videos'].append({'$reference': video_ref})

    def delete(self, force=True, pid=None):
        """Delete a project."""
        videos = video_resolver(self.video_ids)
        # check if I can delete all videos
        if any(video['_deposit'].get('pid') for video in videos):
            raise PIDInvalidAction()
        for video in videos:
            video.delete(force=force)
        return super(Project, self).delete(force=force, pid=pid)

    @has_status(status='draft')
    def reserve_report_number(self):
        """Reserve project's report number until first publishing."""
        report_number_minter(None, self)

    def mint_report_number(self, id_, **kwargs):
        """Mint project's report number."""
        assert self.report_number is not None
        # Register reserved report number
        pid = PersistentIdentifier.get('rn', self.report_number)
        pid.assign('rec', id_, overwrite=True)
        assert pid.register()
        db.session.commit()

    @required(['category', 'type'])
    def get_report_number_sequence(self, **kwargs):
        """Get the sequence generator for Projects."""
        try:
            year = arrow.get(self['date']).year
        except KeyError:
            year = datetime.date.today().year

        return Sequence(self.sequence_name,
                        year=year,
                        category=self['category'],
                        type=self['type']), kwargs

    def _current_tasks_status(self):
        """Return up-to-date tasks status."""
        list_events = [get_deposit_events(depid) for depid in self.video_ids]
        events = list(itertools.chain.from_iterable(list_events))
        return get_tasks_status_by_task(events)


class Video(CDSDeposit):
    """Define API for a video."""

    sequence_name = 'video-v1_0_0'
    """Sequence identifier."""

    _schema = 'deposits/records/video-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a video deposit.

        Adds bucket creation immediately on deposit creation.
        """
        project_id = data.get('_project_id')
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        project = project_resolver(project_id)
        video_new = super(Video, cls).create(data, id_=id_, **kwargs)
        video_new.project = project
        project.commit()
        video_new.commit()
        return video_new

    @property
    def ref(self):
        """Get video id."""
        if self.status == 'published':
            return record_build_url(self['recid'])
        else:
            return video_build_url(self['_deposit']['id'])

    @property
    def project(self):
        """Get the related project."""
        if not hasattr(self, '_project'):
            try:
                project_id = self['_project_id']
            except KeyError:
                return None
            project_pid = PersistentIdentifier.query.filter_by(
                pid_value=project_id).one()
            self._project = Project.get_record(id_=project_pid.object_uuid)
        return self._project

    @project.setter
    def project(self, project):
        """Set a project."""
        self['_project_id'] = project['_deposit']['id']
        project._add_video(self)

    def _tasks_global_status(self):
        """Check if all tasks are successfully."""
        global_status = ComputeGlobalStatus()
        events = get_deposit_events(deposit_id=self['_deposit']['id'])
        iterate_events_results(events=events, fun=global_status)
        return global_status.status

    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a video and update the related project."""
        # save a copy of the old PID
        video_old_id = self['_deposit']['id']
        # check all tasks are successfully
        if self._tasks_global_status() != states.SUCCESS:
            raise PIDInvalidAction()
        # inherit ``category`` and ``type`` fields from parent project
        self['category'] = self.project.get('category')
        self['type'] = self.project.get('type')
        # generate human-readable duration
        self.generate_duration()
        # publish the video
        video_published = super(Video, self).publish(pid=pid, id_=id_,
                                                     **kwargs)
        _, record_new = self.fetch_published()
        # update associated project
        video_published.project._update_videos(
            [video_build_url(video_old_id)],
            [record_build_url(record_new['recid'])]
        )
        video_published.project.commit()
        return video_published

    def edit(self, pid=None):
        """Edit a video and update the related project."""
        # save a copy of the recid
        video_old_id = self['recid']
        # edit the video
        video_new = super(Video, self).edit(pid=pid)
        # update associated project
        video_new.project._update_videos(
            [record_build_url(video_old_id)],
            [video_build_url(video_new['_deposit']['id'])]
        )
        video_new.project.commit()
        assert video_new.report_number
        return video_new

    def _clean_tasks(self):
        """Clean all tasks."""
        events = get_deposit_events(deposit_id=self['_deposit']['id'])
        for event in events:
            event.receiver.delete(event=event)

    def delete(self, force=True, pid=None):
        """Delete a video."""
        ref_old = self.ref
        project = self.project
        # clean tasks
        self._clean_tasks()
        # delete video
        video_deleted = super(Video, self).delete(force=force, pid=pid)
        # update project
        project._delete_videos([ref_old])
        return video_deleted

    def discard(self, pid=None):
        """Discard a video."""
        video_old_ref = self.ref
        video_discarded = super(Video, self).discard(pid=pid)
        video_discarded.project._update_videos(
            [video_old_ref],
            [video_discarded.ref]
        )
        return video_discarded

    def mint_report_number(self, id_, **kwargs):
        """Mint video's report number.

        Makes sure the parent project's report number has been
        reserved. If it has not, it is reserved on the spot.
        """
        if self.project.report_number is None:
            self.project.reserve_report_number()
        super(Video, self).mint_report_number(
            id_, parent_report_number=self.project.report_number)

    @has_status(status='published')
    def get_report_number_sequence(self, **kwargs):
        """Get the sequence generator for Videos."""
        assert 'parent_report_number' in kwargs
        parent_rn = kwargs.pop('parent_report_number')
        parent_name = self.project.sequence_name
        return Sequence(self.sequence_name, **{parent_name: parent_rn}), kwargs

    def _current_tasks_status(self):
        """Return up-to-date tasks status."""
        return get_tasks_status_by_task(
            get_deposit_events(self['_deposit']['id']))

    def generate_duration(self):
        """Generate human-readable duration field."""
        seconds = float(self['_deposit']['extracted_metadata']['duration'])
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        self['duration'] = '{0:02d}:{1:02d}:{2:06.3f}'.format(
            int(hours), int(minutes), seconds)


class Category(Record):
    """Define API for a category."""

    _schema = 'categories/category-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a category."""
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)

        data['suggest_name'] = {
            'input': data.get('name', None),
            'payload': {'types': data.get('types', [])}
        }
        return super(Category, cls).create(data=data, id_=id_, **kwargs)
