# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017, 2018 CERN.
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

import datetime
import os
import re
import uuid
from contextlib import contextmanager
from copy import deepcopy
from functools import partial, wraps
from os.path import splitext

import arrow
from celery import states
from flask import current_app
from flask_security import current_user
from invenio_db import db
from invenio_deposit.api import Deposit, has_status, preserve
from invenio_deposit.utils import mark_as_action
from invenio_files_rest.models import (Bucket, Location, MultipartObject,
                                       ObjectVersion, ObjectVersionTag,
                                       as_bucket, as_object_version)
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.errors import (PIDDoesNotExistError, PIDInvalidAction,
                                     ResolverError)
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.resolver import Resolver
from invenio_records_files.models import RecordsBuckets
from invenio_records_files.utils import sorted_files_from_bucket
from invenio_sequencegenerator.api import Sequence
from jsonschema.exceptions import ValidationError

from ..records.api import (CDSFileObject, CDSFilesIterator, CDSRecord,
                           CDSVideosFilesIterator)
from ..records.minters import doi_minter, is_local_doi, report_number_minter
from ..records.resolver import record_resolver
from ..records.tasks import create_symlinks
from ..records.validators import PartialDraft4Validator
from ..webhooks.status import (ComputeGlobalStatus, get_deposit_events,
                               get_tasks_status_by_task,
                               iterate_events_results, merge_tasks_status)
from .errors import DiscardConflict
from .resolver import get_video_pid

PRESERVE_FIELDS = (
    '_cds',
    '_deposit',
    '_buckets',
    '_files',
    'videos',
    'recid',
    'report_number',
    'publication_date',
    '_project_id',
    'doi',
    '_eos_library_path',
)


def required(fields):
    """Check required fields."""
    def check(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            for field, error in fields.items():
                if field not in self:
                    raise ValidationError(error)
            return f(self, *args, **kwargs)
        return wrapper
    return check


class DummyIndexer(object):
    """Define a dummy indexer to disable Deposit indexer."""

    def index(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass


class CDSDeposit(Deposit):
    """Define API for changing deposit state."""

    indexer = DummyIndexer()
    sequence_name = None
    """Sequence identifier (`None` if not applicable)."""

    file_cls = CDSFileObject

    files_iter_cls = CDSFilesIterator

    published_record_class = CDSRecord

    def __init__(self, *args, **kwargs):
        """Init."""
        super(CDSDeposit, self).__init__(*args, **kwargs)
        self._update_tasks_status()
        self['_files'] = self._get_files_dump()

    @property
    def _bucket(self):
        """Get the bucket object."""
        return as_bucket(self['_buckets']['deposit'])

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
        return deposit

    @classmethod
    def get_records(cls, ids, with_deleted=False):
        """Get records."""
        deposits = super(CDSDeposit, cls).get_records(
            ids=ids, with_deleted=with_deleted)
        return deposits

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a CDS deposit.

        Adds bucket creation immediately on deposit creation.
        """
        if '_deposit' not in data:
            id_ = id_ or uuid.uuid4()
            cls.deposit_minter(id_, data)
        bucket = Bucket.create(location=Location.get_by_name(
                kwargs.get('bucket_location', 'default')))
        data['_buckets'] = {'deposit': str(bucket.id)}
        data.setdefault('_cds', {})
        data['_cds'].setdefault('state', {})
        data.setdefault('keywords', [])
        data.setdefault('license', [{
            'license': 'CERN',
            'material': '',
            'url': 'http://copyright.web.cern.ch',
        }])
        if '_access' not in data:
            data.setdefault('_access', {})
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
        def lower(l):
            return [s.lower() for s in l]
        # use always lower case in the access rights to prevent problems
        if '_access' in self:
            self['_access']['read'] = lower(self['_access'].get('read', []))
            self['_access']['update'] = lower(self['_access'].get('update', []))
        super(CDSDeposit, self).update(*args, **kwargs)

    @preserve(result=False, fields=PRESERVE_FIELDS)
    def patch(self, *args, **kwargs):
        """Patch only drafts."""
        return super(CDSDeposit, self).patch(*args, **kwargs)

    @property
    def report_number(self):
        """Return report number."""
        try:
            return self['report_number'][0]
        except KeyError:
            return None

    @report_number.setter
    def report_number(self, value):
        """Set new report number."""
        self['report_number'] = [value]

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
        return super(CDSDeposit, self).dumps(**kwargs)

    def _update_tasks_status(self):
        """Update tasks status."""
        if '_cds' in self:
            self['_cds']['state'] = self._current_tasks_status()

    def _current_tasks_status(self):
        """Return default. Override method to handle different task status."""
        return {}

    @contextmanager
    def _process_files(self, record_id, data):
        """Snapshot bucket and add files in record during first publishing."""
        if self.files:
            assert not self.files.bucket.locked
            # FIXME deposit bucket is never locked down
            snapshot = self.files.bucket.snapshot()
            for data in self._merge_related_objects(
                record_id=record_id, snapshot=snapshot, data=data
            ):
                yield data
        else:
            yield

    @mark_as_action
    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a deposit."""
        try:
            self['_cds']['modified_by'] = int(current_user.get_id())
        except AttributeError:
            current_app.logger.warning(
                'No current user found, keeping previous value for'
                ' _cds.modified_by')
        if 'publication_date' not in self:
            now = datetime.datetime.utcnow().date().isoformat()
            self['publication_date'] = now
        return super(CDSDeposit, self).publish(pid=pid, id_=id_, **kwargs)

    def has_keyword(self, keyword):
        """Check if the video has the kwyword."""
        kw_ref = keyword.ref
        return any(keyword['$ref'] == kw_ref
                   for keyword in self['keywords'])

    def add_keyword(self, keyword):
        """Add a new keyword."""
        if not self.has_keyword(keyword):
            self['keywords'].append({'$ref': keyword.ref})

    def remove_keyword(self, keyword):
        """Remove a keyword."""
        ref = keyword.ref
        self['keywords'] = list(filter(
            lambda x: x['$ref'] != ref, self['keywords']
        ))

    def has_record(self):
        """Check if deposit is published at least one time."""
        return self['_deposit'].get('pid') is not None

    def is_published(self):
        """Check if deposit is currently published."""
        return self['_deposit']['status'] == 'published'

    def has_minted_doi(self):
        """Check if deposit has a minted DOI."""
        if self.get('doi'):
            return is_local_doi(self['doi']) if self.has_record() else False
        return False  # There is no DOI at all

    def _prepare_edit(self, record):
        """Unlock bucket after edit."""
        data = super(CDSDeposit, self)._prepare_edit(record=record)
        # TODO when you edit we are starting always from the deposit
        return data

    def _publish_edited(self):
        """Sync deposit bucket with the record bucket."""
        record = super(CDSDeposit, self)._publish_edited()
        return self._sync_record_files(record=record)

    def _sync_record_files(self, record):
        """Synchronize deposit files with deposit files."""
        if self.files:
            record.files.bucket.locked = False
            snapshot = self.files.bucket.merge(bucket=record.files.bucket)
            next(self._merge_related_objects(
                record_id=record.id, snapshot=snapshot, data=record
            ))
            record.files.bucket.locked = True

        return record

    def _merge_related_objects(self, record_id, snapshot, data):
        """."""
        # dict of version_ids in original bucket to version_ids in
        # snapshot bucket for the each file
        snapshot_obj_list = ObjectVersion.get_by_bucket(bucket=snapshot)
        old_to_new_version = {
            str(self.files[obj.key]['version_id']): str(obj.version_id)
            for obj in snapshot_obj_list
            if 'master' not in obj.get_tags() and obj.key in self.files}
        # list of tags with 'master' key
        slave_tags = [tag for obj in snapshot_obj_list for tag in obj.tags
                      if tag.key == 'master']
        # change master of slave videos to new master object versions
        for tag in slave_tags:
            # note: the smil file probably already point to the right
            # record bucket and it doesn't need update
            new_master_id = old_to_new_version.get(tag.value)
            if new_master_id:
                tag.value = new_master_id
        db.session.add_all(slave_tags)

        # FIXME bug when dump a different bucket
        backup = deepcopy(self['_files'])

        # Generate SMIL file
        data['_files'] = self.files.dumps(bucket=snapshot.id)

        master_video = get_master_object(snapshot)
        if master_video:
            from cds.modules.records.serializers.smil import generate_smil_file
            generate_smil_file(record_id, data, snapshot, master_video)

        # Update metadata with SMIL file information
        data['_files'] = self.files.dumps(bucket=snapshot.id)

        # FIXME bug when dump a different bucket
        self['_files'] = backup

        snapshot.locked = True

        yield data
        db.session.add(RecordsBuckets(
            record_id=record_id, bucket_id=snapshot.id
        ))


# TODO move inside Video class
def video_build_url(video_id):
    """Build video url."""
    return 'https://cds.cern.ch/api/deposits/video/{0}'.format(str(video_id))


# TODO move inside Video class
def record_build_url(video_id):
    """Build video url."""
    return 'https://cds.cern.ch/api/record/{0}'.format(str(video_id))


def record_unbuild_url(url):
    """Extract the PID from the deposit/record url."""
    # TODO can we improve it?
    return os.path.basename(url)


def is_deposit(url):
    """Check if it's a deposit or a record."""
    # TODO can we improve check?
    try:
        return 'deposit' in url
    except TypeError:
        return False


def get_master_object(bucket):
    """Get master ObjectVersion from a bucket."""
    # TODO do as we do in `get_master_video_file()`?
    return ObjectVersion.get_by_bucket(bucket).join(
        ObjectVersionTag
    ).filter(
        ObjectVersionTag.key == 'context_type',
        ObjectVersionTag.value == 'master'
    ).one_or_none()


def is_project_record(record):
    """Check if it is a project record."""
    project_schema = current_app.config['DEPOSIT_JSONSCHEMAS_PREFIX'] + \
        current_jsonschemas.url_to_path(record['$schema'])
    return project_schema == Project._schema


class Project(CDSDeposit):
    """Define API for a project."""

    sequence_name = 'project-v1_0_0'
    """Sequence identifier."""

    _schema = 'deposits/records/videos/project/project-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a project deposit.

        Adds bucket creation immediately on deposit creation.
        """
        kwargs.setdefault('bucket_location', 'videos')
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        data.setdefault('videos', [])
        data.setdefault('_access', {})
        data.setdefault('_cds', {})
        # Add the current user to the ``_access.update`` list
        try:
            data['_access']['update'] = [current_user.email]
            data['_cds']['current_user_mail'] = current_user.email
        except AttributeError:
            current_app.logger.warning(
                'No current user found, _access.update will stay empty.')
        return super(Project, cls).create(data, id_=id_, **kwargs)

    @property
    def video_ids(self):
        """Get all video ids.

        .. note::

            If the video is published, it returns the recid.
            Otherwise, the ``video['_deposit']['id']``.

        :returns: A list of video ids.
        """
        if len(self['videos']) > 0 and self['videos'][0].get('$ref', ''):
            return [record_unbuild_url(ref) for ref in self._video_refs]

        #  return []
        ids = []
        for video in self['videos']:
            if Video(video).is_published():
                ids.append(video['_deposit'].get('pid'))
            else:
                ids.append(video['_deposit']['id'])
        return ids

    @property
    def _video_refs(self):
        """Get all video refs.

        :returns: A list of video references.
        """
        refs = []
        for video in self.get('videos', []):
            if '$ref' in video:
                refs.append(video['$ref'])
            else:
                refs.append(Video(video).ref)
        return refs

    def _find_refs(self, refs):
        """Find index of references."""
        result = {}
        for (key, value) in enumerate(self._video_refs):
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
        for (key, value) in enumerate(self._video_refs):
            try:
                index = old_refs.index(value)
                self['videos'][key] = {'$ref': new_refs[index]}
            except ValueError:
                pass

    def _delete_videos(self, refs):
        """Update metadata deleting videos.

        :param refs: List contains the video references to delete.
        """
        for index in self._find_refs(refs).keys():
            del self['videos'][index]

    def _publish_videos(self):
        """Publish all videos that are still deposits."""
        # get reference of all video deposits still not published
        refs_old = [video_ref for video_ref in self._video_refs
                    if is_deposit(video_ref)]

        # extract the PIDs from the video deposits
        ids_old = [record_unbuild_url(video_ref) for video_ref in refs_old]

        # publish them and get the new PID
        videos_published = [video.publish().commit()
                            for video in deposit_videos_resolver(ids_old)]

        # get new video references
        refs_new = [record_build_url(video['recid'])
                    for video in videos_published]

        # update project video references
        self._update_videos(refs_old, refs_new)

        return videos_published

    def _publish_new(self, id_=None):
        """Publish new project and update all the video pointers."""
        record = super(Project, self)._publish_new(id_=id_)
        patch = [{
            'op': 'replace',
            'path': '/_project_id',
            'value': str(record['recid'])
        }]
        for video_id in self.video_ids:
            video = CDSRecord.get_record(
                record_resolver.resolve(video_id)[0].object_uuid)
            video.patch(patch).commit()
        return record

    @mark_as_action
    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a project.

        The publishing involve the publication of all the videos inside.

        :returns: The new project version.
        """
        # make sure all video are published
        self._publish_videos()
        # Return project with generated report number
        self = Project(self.model.json, self.model)
        assert self.report_number
        # publish project
        return super(Project, self).publish(pid=pid, id_=id_, **kwargs)

    @mark_as_action
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
            self['videos'][indices[video_ref]] = {'$ref': video_ref}
        else:
            # add new one
            self['videos'].append({'$ref': video_ref})

    def delete(self, force=True, pid=None):
        """Delete a project."""
        videos = deposit_videos_resolver(self.video_ids)
        # check if I can delete all videos
        if any(video['_deposit'].get('pid') for video in videos):
            raise PIDInvalidAction()
        # delete all videos
        for video in videos:
            video.delete(force=force)
            # mark video PIDs as DELETED
            pid = get_video_pid(pid_value=video['_deposit']['id'])
            if not pid.is_deleted():
                pid.delete()
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

    @required({
        'category': 'Category field not found in the project',
        'type': 'Type field not found in the project',
    })
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
        status = {}
        for video in self.videos:
            status = merge_tasks_status(
                status, video['_cds'].get('state', {}))
        return status

    @classmethod
    def build_video_ref(cls, video):
        """Build the video reference."""
        if video.is_published():
            url = record_build_url(video['_deposit']['pid']['value'])
        else:
            url = video_build_url(video['_deposit']['id'])
        return {'$ref': url}

    @property
    def videos(self):
        """Get videos."""
        videos = []
        for ref in self._video_refs:
            if is_deposit(ref):
                videos.append(deposit_video_resolver(record_unbuild_url(ref)))
            else:
                videos.append(record_resolver.resolve(
                    record_unbuild_url(ref)
                )[1])
        return videos

    def update(self, *args, **kwargs):
        """Update project."""
        super(Project, self).update(*args, **kwargs)
        self._sync_videos()
        return self

    def _sync_videos(self):
        """Sync fields from project to the videos."""
        # sync access right from project to the videos
        for video in self.videos:
            # sync video with project
            if self._sync_fields(video=video):
                video.commit(validator=PartialDraft4Validator)
            if not isinstance(video, Video):
                # if it's a record, sync also video deposit
                deposit_video = deposit_video_resolver(video['_deposit']['id'])
                if self._sync_fields(video=deposit_video):
                    deposit_video.commit(validator=PartialDraft4Validator)

    def _sync_fields(self, video):
        """Sync some fields from project."""
        changed = False
        # Only change metadata if the video is not published
        project_access = self.get('_access', {}).get('update')
        project_created_by = self['_deposit'].get('created_by')

        if video.get('_access', {}).get('update') != project_access \
                and project_access:
            changed = True
            # sync access rights
            if '_access' in video:
                video['_access']['update'] = deepcopy(project_access)
            else:
                video['_access'] = dict(update=deepcopy(project_access))
        if video['_deposit'].get('created_by') != project_created_by:
            changed = True
            # sync owner
            video['_deposit']['created_by'] = project_created_by

        return changed


class Video(CDSDeposit):
    """Define API for a video."""

    sequence_name = 'video-v1_0_0'
    """Sequence identifier."""

    _schema = 'deposits/records/videos/video/video-v1.0.0.json'

    _tasks_initial_state = {
        'file_transcode': states.PENDING,
        'file_video_extract_frames': states.PENDING,
        'file_video_metadata_extraction': states.PENDING
    }

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a video deposit.

        Adds bucket creation immediately on deposit creation.
        """
        kwargs.setdefault('bucket_location', 'videos')
        project_id = data.get('_project_id')
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        # set default copyright
        data.setdefault('copyright', {
            'holder': 'CERN',
            'year': str(datetime.date.today().year),
            'url': 'http://copyright.web.cern.ch',
        })
        data.setdefault('_cds', {})
        data['_cds'].setdefault('state', cls._tasks_initial_state)

        project = deposit_project_resolver(project_id)
        # create video
        video_new = super(Video, cls).create(data, id_=id_, **kwargs)
        # set video project
        video_new.project = project
        # copy access rights from project
        project._sync_fields(video=video_new)
        # copy license only at creation time
        if not video_new.get('license'):
            video_new['license'] = deepcopy(project.get('license'))

        project.commit()
        video_new.commit()
        return video_new

    @property
    def ref(self):
        """Get video url (for the record if it's published)."""
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
            try:
                # get the deposit project
                self._project = deposit_project_resolver(project_id=project_id)
            except PIDDoesNotExistError:
                # get the record project
                _, record = record_resolver.resolve(project_id)
                project_id = record['_deposit']['id']
                self._project = deposit_project_resolver(project_id=project_id)
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

    def _rename_subtitles(self):
        """Rename subtitles."""
        # Pattern to extract subtitle's filename and iso language
        pattern = re.compile('.*_(?P<iso_lang>[a-zA-Z]{2})\.vtt$')
        subtitles = CDSVideosFilesIterator.get_video_subtitles(self)
        for subtitle_file in subtitles:
            subtitle_obj = as_object_version(subtitle_file['version_id'])
            match = pattern.match(subtitle_file['key'])
            if match:
                subtitle_obj.key = '{}_{}.vtt'.format(self['report_number'][0],
                                                      match.group('iso_lang'))
                db.session.add(subtitle_obj)

    def _rename_master_file(self, master_file):
        """Rename master file."""
        master_obj = as_object_version(master_file['version_id'])
        master_obj.key = '{}.{}'.format(
            self['report_number'][0],
            master_file.get('content_type')
            or splitext(master_file['key'])[1][1:].lower())
        db.session.add(master_obj)

    def _publish_new(self, id_=None):
        """Rename master file and subtitles and publish for the first time."""
        id_ = id_ or uuid.uuid4()
        self.mint_report_number(id_)
        self['_files'] = self.files.dumps()

        master_file = CDSVideosFilesIterator.get_master_video_file(self)
        # This is needed because in tests there is not always a master file
        # FIXME refactor tests to include always a master file when publishing
        if master_file:
            self._rename_master_file(master_file)
            self._rename_subtitles()
        return super(CDSDeposit, self)._publish_new(id_)

    def _publish_edited(self):
        """Rename subtitles and publish."""
        self['_files'] = self.files.dumps()
        self._rename_subtitles()

        from cds.modules.records.permissions import is_public
        if is_public(self, 'read'):
            # Mint the doi if necessary
            doi_minter(record_uuid=self.id, data=self)

        return super(Video, self)._publish_edited()

    @mark_as_action
    def publish(self, pid=None, id_=None, **kwargs):
        """Publish a video and update the related project."""
        # save a copy of the old PID
        video_old_id = self['_deposit']['id']
        try:
            self['category'] = self.project['category']
            self['type'] = self.project['type']
        except KeyError:
            raise ValidationError(
                message='category and/or type not found in the project')
        if '_access' not in self:
            self['_access'] = {}
        self['_access']['update'] = self.project.get(
            '_access', {}).get('update', [])
        self.project._sync_fields(self)
        # generate human-readable duration
        self.generate_duration()
        # generate extra tags for files
        self._create_tags()

        previous_record = None
        if 'pid' in self['_deposit']:
            try:
                _, previous_record = self.fetch_published()
                previous_record = deepcopy(previous_record)
            except ResolverError:
                # video not yet published
                pass

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

        # create file symlinks delayed (waiting the commit)
        create_symlinks.s(
            previous_record=previous_record, record_uuid=str(record_new.id)
        ).apply_async(countdown=90)

        return video_published

    @mark_as_action
    def edit(self, pid=None):
        """Edit a video and update the related project."""
        # save a copy of the recid
        video_old_id = self['recid']
        # edit the video
        video_new = super(Video, self).edit(pid=pid)
        # update project reference from recid to depid
        video_new['_project_id'] = self.project['_deposit']['id']
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

    @mark_as_action
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
        project.commit()
        return video_deleted

    @mark_as_action
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
            get_deposit_events(self['_deposit']['id']),
            statuses=deepcopy(self['_cds'].get('state', {})))

    def generate_duration(self):
        """Generate human-readable duration field."""
        seconds = float(self['_cds']['extracted_metadata']['duration'])
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        self['duration'] = '{0:02d}:{1:02d}:{2:02d}'.format(
            int(hours), int(minutes), int(seconds))

    def _create_tags(self):
        """Create additional tags."""
        # Subtitle file
        pattern = re.compile(".*_([a-zA-Z]{2})\.vtt$")
        objs = [o for o in sorted_files_from_bucket(self._bucket)
                if pattern.match(o.key)]
        with db.session.begin_nested():
            for obj in objs:
                # language tag
                found = pattern.findall(obj.key)
                if len(found) == 1:
                    lang = found[0]
                    ObjectVersionTag.create_or_update(obj, 'language', lang)
                else:
                    # clean to be sure there is no some previous value
                    ObjectVersionTag.delete(obj, 'language')
                # other tags
                ObjectVersionTag.create_or_update(obj, 'content_type', 'vtt')
                ObjectVersionTag.create_or_update(
                    obj, 'context_type', 'subtitle')
                ObjectVersionTag.create_or_update(
                    obj, 'media_type', 'subtitle')
                # refresh object
                db.session.refresh(obj)

            # Poster frame
            pattern = re.compile('^poster\.(jpg|png)$')
            try:
                poster = [o for o in sorted_files_from_bucket(self._bucket)
                          if pattern.match(o.key)][0]
            except IndexError:
                return

            ext = pattern.findall(poster.key)[0]
            # frame tags
            ObjectVersionTag.create_or_update(poster, 'content_type', ext)
            ObjectVersionTag.create_or_update(poster, 'context_type', 'poster')
            ObjectVersionTag.create_or_update(poster, 'media_type', 'image')
            # refresh object
            db.session.refresh(poster)


project_resolver = Resolver(
    pid_type='depid', object_type='rec',
    getter=partial(Project.get_record, with_deleted=True)
)


video_resolver = Resolver(
    pid_type='depid', object_type='rec',
    getter=partial(Video.get_record, with_deleted=True)
)


def deposit_project_resolver(project_id):
    """Resolve project."""
    _, deposit = project_resolver.resolve(project_id)
    return deposit


def deposit_video_resolver(video_id):
    """Resolve video."""
    _, deposit = video_resolver.resolve(video_id)
    return deposit


def deposit_videos_resolver(video_ids):
    """Resolve videos."""
    return [deposit_video_resolver(id_) for id_ in video_ids]


def record_video_resolver(video_id):
    """Get the video deposit from the record."""
    return Video.get_record(record_resolver.resolve(video_id)[1].id)


def record_project_resolver(video_id):
    """Get the video deposit from the record."""
    return Project.get_record(record_resolver.resolve(video_id)[1].id)
