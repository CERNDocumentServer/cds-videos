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
"""Celery tasks for Webhook Receivers."""

from __future__ import absolute_import

import fnmatch
import hashlib
import json
import jsonpatch
import os
import requests
import shutil
import signal
import tempfile
import time
from functools import partial

from PIL import Image
from cds_sorenson.api import get_encoding_status, start_encoding, stop_encoding
from cds_sorenson.error import InvalidResolutionError
from celery import Task, shared_task, current_app as celery_app, chain
from celery.states import FAILURE, STARTED, SUCCESS, REVOKED

from invenio_db import db
from invenio_files_rest.models import (FileInstance, ObjectVersion,
                                       ObjectVersionTag, as_object_version)
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_sse import current_sse
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import ConcurrentModificationError
from invenio_indexer.api import RecordIndexer
from werkzeug.utils import import_string

from ..deposit.api import video_resolver, CDSDeposit
from ..ffmpeg import ff_frames, ff_probe_all


def sse_publish_event(channel, type_, state, meta):
    """Publish a message on SSE channel."""
    if channel:
        data = {'state': state, 'meta': meta}
        current_sse.publish(data=data, type_=type_, channel=channel)


class AVCTask(Task):
    """Base class for tasks which might be sending SSE messages."""

    abstract = True

    def __init__(self, type_):
        """Constructor."""
        super(AVCTask, self).__init__()
        self._base_payload = {'type': type_}
        self._type = type_

    def _extract_call_arguments(self, arg_list, **kwargs):
        for name in arg_list:
            setattr(self, name, kwargs.pop(name, None))
        return kwargs

    def __call__(self, *args, **kwargs):
        """Extract SSE channel from keyword arguments.

        .. note ::
            the channel is extracted from the ``sse_channel`` keyword
            argument.
        """
        arg_list = [
            'sse_channel', 'event_id', 'deposit_id', 'bucket_id', 'key']
        kwargs = self._extract_call_arguments(arg_list, **kwargs)

        with self.app.flask_app.app_context():
            self.object = as_object_version(kwargs.pop('version_id', None))
            if self.object:
                self.obj_id = str(self.object.version_id)
            return self.run(*args, **kwargs)

    def update_state(self, task_id=None, state=None, meta=None):
        """."""
        self._base_payload.update(meta.get('payload', {}))
        meta['payload'] = self._base_payload
        super(AVCTask, self).update_state(task_id, state, meta)
        sse_publish_event(channel=self.sse_channel, type_=self._type,
                          state=state, meta=meta)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """When an error occurs, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            meta = dict(message=str(exc), payload=self._base_payload)
            # NOTE: workaround to be able to save the meta in case of exception
            exception = {}
            exception['exc_message'] = meta
            exception['exc_type'] = 'TypeError'
            self.update_state(task_id=task_id, state=FAILURE, meta=exception)
            # /NOTE
            self._update_record()

    def on_success(self, exc, task_id, *args, **kwargs):
        """When end correctly, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            meta = dict(message=str(exc), payload=self._base_payload)
            self.update_state(task_id=task_id, state=SUCCESS, meta=meta)
            self._update_record()

    def _update_record(self):
        # update record state
        with celery_app.flask_app.app_context():
            if 'deposit_id' in self._base_payload \
                    and self._base_payload['deposit_id']:
                update_avc_deposit_state(
                    deposit_id=self._base_payload.get('deposit_id'),
                    event_id=self._base_payload.get('event_id'),
                    sse_channel=self.sse_channel
                )

    @staticmethod
    def set_revoke_handler(handler):
        """Set handler to be executed when the task gets revoked."""
        def _handler(signum, frame):
            handler()
        signal.signal(signal.SIGTERM, _handler)


class DownloadTask(AVCTask):
    """Download task."""

    def __init__(self):
        """Init."""
        self._type = 'file_download'
        self._base_payload = {}  # {'type': self._type}

    def clean(self, version_id, *args, **kwargs):
        """Undo download task."""
        # Delete the file and the object version
        dispose_object_version(version_id)

    def run(self, uri, **kwargs):
        r"""Download file from a URL.

        :param self: reference to instance of task base class
        :param uri: URL of the file to download.
        """
        self._base_payload.update(
            key=self.object.key,
            version_id=self.obj_id,
            tags=self.object.get_tags(),
            event_id=self.event_id,
            deposit_id=self.deposit_id, )

        # Make HTTP request
        response = requests.get(uri, stream=True)

        if 'Content-Length' in response.headers:
            headers_size = int(response.headers.get('Content-Length'))
        else:
            headers_size = None

        def progress_updater(size, total):
            """Progress reporter."""
            size = size or headers_size
            if size is None:
                # FIXME decide on proper error-handling behaviour
                raise RuntimeError('Cannot locate "Content-Length" header.')
            meta = dict(
                payload=dict(
                    size=size,
                    total=total,
                    percentage=total * 100 / size, ),
                message='Downloading {0} of {1}'.format(total, size), )

            self.update_state(state=STARTED, meta=meta)

        self.object.set_contents(response.raw,
                                 progress_callback=progress_updater,
                                 size=headers_size)

        db.session.commit()

        return self.obj_id


class ExtractMetadataTask(AVCTask):
    """Extract metadata task."""

    def __init__(self):
        """Init."""
        self._type = 'file_video_metadata_extraction'
        self._base_payload = {}  # {'type': self._type}
        format_keys = [
            'duration',
            'bit_rate',
            'size',
        ]
        stream_keys = [
            'avg_frame_rate',
            'codec_name',
            'width',
            'height',
            'nb_frames',
            'display_aspect_ratio',
            'color_range',
        ]
        self._all_keys = format_keys + stream_keys

    def clean(self, deposit_id, version_id, *args, **kwargs):
        """Undo metadata extraction."""
        # 1. Revert patch on record
        recid = str(PersistentIdentifier.get(
            'depid', deposit_id).object_uuid)
        patch = [{
            'op': 'remove',
            'path': '/_deposit/extracted_metadata',
        }]
        validator = 'invenio_records.validators.PartialDraft4Validator'
        patch_record(recid=recid, patch=patch, validator=validator)

        # 2. delete every tag created
        for tag in ObjectVersionTag.query.filter(
                ObjectVersionTag.version_id == version_id,
                ObjectVersionTag.key.in_(self._all_keys)).all():
            db.session.delete(tag)

    def run(self, uri=None, *args, **kwargs):
        """Extract metadata from given video file.

        All technical metadata, i.e. bitrate, will be translated into
        ``ObjectVersionTags``, plus all the metadata extracted will be
        store under ``_deposit`` as ``extracted_metadata``.

        :param self: reference to instance of task base class
        :param uri: URL of the file to extract metadata from.
        """
        recid = str(PersistentIdentifier.get(
            'depid', self.deposit_id).object_uuid)
        uri = uri or self.object.file.uri

        self._base_payload.update(
            version_id=str(self.object.version_id),
            uri=uri,
            tags=self.object.get_tags(),
            deposit_id=self.deposit_id,
            event_id=self.event_id, )

        # Extract video's metadata using `ff_probe`
        metadata = json.loads(ff_probe_all(uri))
        extracted_dict = dict(metadata['format'], **metadata['streams'][0])

        # Add technical information to the ObjectVersion as Tags
        [ObjectVersionTag.create(self.object, k, v)
         for k, v in extracted_dict.items()
         if k in self._all_keys]

        tags = self.object.get_tags()

        db.session.commit()

        # Insert metadata into deposit's metadata
        patch = [{
            'op': 'add',
            'path': '/_deposit/extracted_metadata',
            'value': metadata
        }]
        update_record.s(recid, patch).apply()

        # Update state
        self.update_state(
            state=SUCCESS,
            meta=dict(
                payload=dict(tags=tags,),
                message='Attached video metadata'))


class ExtractFramesTask(AVCTask):
    """Extract frames task."""

    def __init__(self):
        """Init."""
        self._type = 'file_video_extract_frames'
        self._base_payload = {}  # {'type': self._type}

    def clean(self, version_id, *args, **kwargs):
        """Delete generated ObjectVersion slaves."""
        # remove all objects version "slave" with type "frame" and,
        # automatically, all tags connected
        tag_alias_1 = aliased(ObjectVersionTag)
        tag_alias_2 = aliased(ObjectVersionTag)
        slaves = ObjectVersion.query \
            .join(tag_alias_1, ObjectVersion.tags) \
            .join(tag_alias_2, ObjectVersion.tags) \
            .filter(
                tag_alias_1.key == 'master',
                tag_alias_1.value == version_id) \
            .filter(tag_alias_2.key == 'type', (tag_alias_2.value == 'frame')
                    | (tag_alias_2.value == 'gif-preview')) \
            .all()
        # FIXME do a test for check separately every "undo" when
        # run a AVC workflow
        for slave in slaves:
            dispose_object_version(slave)

    def run(self, frames_start=5, frames_end=95, frames_gap=1,
            *args, **kwargs):
        """Extract images from some frames of the video.

        Each of the frame images generates an ``ObjectVersion`` tagged as
        "frame" using ``ObjectVersionTags``.

        :param self: reference to instance of task base class
        :param frames_start: start percentage, default 5.
        :param frames_end: end percentage, default 95.
        :param frames_gap: percentage between frames from start to end,
            default 10.
        """
        output_folder = tempfile.mkdtemp()
        in_output = partial(os.path.join, output_folder)

        # Remove temporary directory on abrupt execution halts.
        self.set_revoke_handler(lambda: shutil.rmtree(output_folder,
                                                      ignore_errors=True))

        self._base_payload.update(
            version_id=self.obj_id,
            tags=self.object.get_tags(),
            deposit_id=self.deposit_id,
            event_id=self.event_id, )

        def progress_updater(seconds, duration):
            """Progress reporter."""
            meta = dict(
                payload=dict(
                    size=duration,
                    percentage=(seconds or 0.0) / duration * 100, ),
                message='Extracting frames {0} of {1} seconds'.format(
                    seconds, duration), )

            self.update_state(state=STARTED, meta=meta)

        # Generate frames
        ff_frames(
            self.object.file.uri,
            frames_start,
            frames_end,
            frames_gap,
            os.path.join(output_folder, 'frame-%d.jpg'),
            progress_callback=progress_updater)
        frames = os.listdir(output_folder)

        # Generate GIF for previewing on hover
        gif_name = 'hover_preview.gif'
        images = [Image.open(in_output(frame)) for frame in frames]
        head, tail = images[0], images[1:]
        head.save(in_output(gif_name), save_all=True,
                  append_images=tail, duration=500)

        def create_object(key, type_tag):
            obj = ObjectVersion.create(
                bucket=self.object.bucket,
                key=key,
                stream=open(in_output(key), 'rb'))
            ObjectVersionTag.create(obj, 'master', self.obj_id)
            ObjectVersionTag.create(obj, 'type', type_tag)

        # Create GIF object
        create_object(gif_name, 'gif-preview')

        # Create frame objects
        [create_object(filename, 'frame') for filename in frames]

        shutil.rmtree(output_folder)
        db.session.commit()


class TranscodeVideoTask(AVCTask):
    """Transcode video task."""

    def __init__(self):
        """Init."""
        self._type = 'file_transcode'
        self._base_payload = {}  # {'type': self._type}

    @staticmethod
    def _build_slave_key(preset_quality, master_key):
        """Build the object version key connected with the transcoding."""
        base_name, extension = master_key.rsplit('.', 1)
        return '{0}[{1}].{2}'.format(base_name, preset_quality, extension)

    # FIXME maybe we need to move this part to CDS-Sorenson
    @staticmethod
    def _clean_file_name(uri):
        """Remove file extension from file name.

        For some reason the Sorenson Server adds the extension to the output
        file, creating ``data.mp4``. Our file storage does not use extensions
        and this is causing troubles.
        The best/dirtiest solution is to remove the file extension once the
        transcoded file is created.
        """
        folder = os.path.dirname(uri)
        for file_ in os.listdir(folder):
            if fnmatch.fnmatch(file_, 'data.*'):
                os.rename(os.path.join(folder, file_),
                          os.path.join(folder, 'data'))

    def clean(self, version_id, preset_quality, *args, **kwargs):
        """Delete generated ObjectVersion slaves."""
        object_version = as_object_version(version_id)
        obj_key = self._build_slave_key(
            preset_quality=preset_quality, master_key=object_version.key)
        object_version = ObjectVersion.query.filter_by(
            bucket_id=object_version.bucket_id, key=obj_key).first()
        dispose_object_version(object_version)

    def run(self, preset_quality, sleep_time=5, *args, **kwargs):
        """Launch video transcoding.

        For each of the presets generate a new ``ObjectVersion`` tagged as
        slave with the preset name as key and a link to the master version.

        :param self: reference to instance of task base class
        :param preset_quality: preset quality to use for transcoding.
        :param sleep_time: time interval between requests for the Sorenson
            status.
        """
        self._base_payload.update(
            version_id=str(self.object.version_id),
            preset_quality=preset_quality,
            tags=self.object.get_tags(),
            deposit_id=self.deposit_id,
            event_id=self.event_id, )

        # Get master file's bucket_id
        bucket_id = self.object.bucket_id
        bucket_location = self.object.bucket.location.uri
        # Get master file's key
        master_key = self.object.key
        # Get master file's aspect ratio
        aspect_ratio = self.object.get_tags()['display_aspect_ratio']

        with db.session.begin_nested():
            # Create FileInstance
            file_instance = FileInstance.create()

            # Create ObjectVersion
            obj_key = self._build_slave_key(
                preset_quality=preset_quality, master_key=master_key)
            obj = ObjectVersion.create(bucket=bucket_id, key=obj_key)

            # Extract new location
            storage = file_instance.storage(default_location=bucket_location)
            directory, filename = storage._get_fs()

            input_file = self.object.file.uri
            output_file = os.path.join(directory.root_path, filename)

            try:
                # Start Sorenson
                job_id = start_encoding(input_file, output_file,
                                        preset_quality, aspect_ratio)
            except InvalidResolutionError as e:
                self.update_state(
                    state=REVOKED,
                    meta={'payload': {}, 'message': str(e)})
                return

            # Set revoke handler, in case of an abrupt execution halt.
            self.set_revoke_handler(partial(stop_encoding, job_id))

            # Create ObjectVersionTags
            ObjectVersionTag.create(obj, 'master', self.obj_id)
            ObjectVersionTag.create(obj, '_sorenson_job_id', job_id)
            ObjectVersionTag.create(obj, 'preset_quality', preset_quality)
            ObjectVersionTag.create(obj, 'type', 'video')

            # Information necessary for monitoring
            job_info = dict(
                preset_quality=preset_quality,
                job_id=job_id,
                file_instance=str(file_instance.id),
                uri=output_file,
                version_id=str(obj.version_id),
                key=obj_key,
                tags=obj.get_tags(),
                percentage=0, )

        db.session.commit()

        self.update_state(
            state=STARTED,
            meta=dict(
                payload=dict(job_info=job_info),
                message='Started transcoding.'))

        status = ''
        # Monitor job and report accordingly
        while status != 'Finished':
            # Get job status
            status, percentage = get_encoding_status(job_id)
            if status == 'Error':
                raise RuntimeError('Error transcoding')
            job_info['percentage'] = percentage

            # Update task's state for this preset
            self.update_state(
                state=STARTED,
                meta=dict(
                    payload=dict(**job_info),
                    message='Transcoding {0}'.format(percentage)))

            time.sleep(sleep_time)

        # Set file's location, if job has completed
        self._clean_file_name(output_file)
        with db.session.begin_nested():
            uri = output_file
            with open(uri, 'rb') as transcoded_file:
                digest = hashlib.md5(transcoded_file.read()).hexdigest()
            size = os.path.getsize(uri)
            checksum = '{0}:{1}'.format('md5', digest)
            file_instance.set_uri(uri, size, checksum)
            as_object_version(
                job_info['version_id']).set_file(file_instance)
        db.session.commit()


def patch_record(recid, patch, validator=None):
    """Patch a record."""
    with db.session.begin_nested():
        record = Record.get_record(recid)
        record = record.patch(patch)
        if validator:
            validator = import_string(validator)
        record.commit(validator=validator)
    return record


#
# Patch record
#
@shared_task(bind=True)
def update_record(self, recid, patch, validator=None,
                  max_retries=5, countdown=5):
    """Update a given record with a patch.

    Retries ``max_retries`` after ``countdown`` seconds.

    :param recid: the UUID of the record.
    :param patch: the patch operation to apply.
    :param validator: a jsonschema validator.
    :param max_retries: times to retry operation.
    :param countdown: time to sleep between retries.
    """
    if patch:
        try:
            patch_record(recid=recid, patch=patch,
                         validator=validator)
            db.session.commit()
            return recid
        except ConcurrentModificationError as exc:
            db.session.rollback()
            raise self.retry(
                max_retries=max_retries, countdown=countdown, exc=exc)


def get_patch_tasks_status(deposit):
    """Get the patch to apply to update record tasks status."""
    old_status = deposit['_deposit']['state']
    new_status = deposit._current_tasks_status()
    # create tasks status patch
    patches = jsonpatch.make_patch(old_status, new_status).patch
    # make it suitable for the deposit
    for patch in patches:
        patch['path'] = '/_deposit/state{0}'.format(patch['path'])
    return patches


@shared_task
def spread_deposit_update(id_=None, event_id=None, sse_channel=None):
    """If record is updated correctly, spread the news."""
    if id_:
        # get_record
        deposit = CDSDeposit.get_record(id_)
        # send a message to SSE
        sse_publish_event(
            channel=sse_channel, type_='update_deposit', state=SUCCESS,
            meta={
                'payload': {
                    'deposit': deposit,
                    'event_id': event_id,
                    'deposit_id': deposit['_deposit']['id'],
                }
            })
        # send deposit to the reindex queue
        RecordIndexer().bulk_index(iter([id_]))


def update_avc_deposit_state(deposit_id=None, event_id=None, sse_channel=None,
                             **kwargs):
    """Update deposit state on SSE and ElasticSearch."""
    if deposit_id:
        # get video
        video = video_resolver([deposit_id])[0]
        # create the patch for video
        video_patch = get_patch_tasks_status(deposit=video)
        project_patch = None
        project_id = None
        if video.project:
            project_patch = get_patch_tasks_status(deposit=video.project)
            project_id = video.project.id
        # update record
        if video_patch:
            validator = 'invenio_records.validators.PartialDraft4Validator'
            chain(
                update_record.s(recid=str(video.id), patch=video_patch,
                                validator=validator),
                spread_deposit_update.s(event_id=str(event_id),
                                        sse_channel=sse_channel),
                update_record.si(recid=str(project_id),
                                 patch=project_patch, validator=validator),
                spread_deposit_update.s(event_id=str(event_id),
                                        sse_channel=sse_channel)
            ).apply_async()


def dispose_object_version(object_version):
    """Clean up resources related to an ObjectVersion."""
    # TODO move the "file removal" in a separate function to be able to
    # remove the file from download without remove the object version.
    # See: AVC workflow download task (clean)
    if object_version:
        object_version = as_object_version(object_version)
        file_id = object_version.file_id
        object_version.remove()
        if file_id:
            # TODO add a "force" option on remove_file_data() task?
            #  remove_file_data.s(file_id, silent=False).apply_async()
            f = FileInstance.get(file_id)
            f.delete()
            f.storage().delete()
