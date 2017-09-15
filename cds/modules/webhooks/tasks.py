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
"""Celery tasks for Webhook Receivers."""

from __future__ import absolute_import

import fnmatch
import hashlib
import logging
import os
import shutil
import signal
import tempfile
import time
from functools import partial

import jsonpatch
import requests
from cds_sorenson.api import (get_encoding_status, get_preset_info,
                              start_encoding, stop_encoding)
from cds_sorenson.error import InvalidResolutionError, TooHighResolutionError
from celery import current_app as celery_app
from celery import Task, shared_task
from celery.exceptions import Ignore
from celery.states import FAILURE, REVOKED, STARTED, SUCCESS
from celery.utils.log import get_task_logger
from flask_iiif.utils import create_gif_from_frames
from invenio_db import db
from invenio_files_rest.models import (FileInstance, ObjectVersion,
                                       ObjectVersionTag, as_object_version)
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_sse import current_sse
from PIL import Image
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import ConcurrentModificationError
from werkzeug.utils import import_string

from ..deposit.api import deposit_video_resolver
from ..ffmpeg import ff_frames, ff_probe_all
from ..xrootd.utils import file_opener_xrootd, replace_xrootd

logger = get_task_logger(__name__)


def sse_publish_event(channel, type_, state, meta):
    """Publish a message on SSE channel."""
    if channel:
        data = {'state': state, 'meta': meta}
        current_sse.publish(data=data, type_=type_, channel=channel)


class AVCTask(Task):
    """Base class for tasks which might be sending SSE messages."""

    abstract = True

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
        arg_list = ['sse_channel', 'event_id', 'deposit_id', 'key']
        kwargs = self._extract_call_arguments(arg_list, **kwargs)

        with self.app.flask_app.app_context():
            if kwargs.get('_clean', False):
                self.clean(*args, **kwargs)

            self.object = as_object_version(kwargs.pop('version_id', None))
            if self.object:
                self.obj_id = str(self.object.version_id)
            self.set_base_payload()
            return self.run(*args, **kwargs)

    def update_state(self, task_id=None, state=None, meta=None):
        """."""
        self._base_payload.update(meta.get('payload', {}))
        meta['payload'] = self._base_payload
        super(AVCTask, self).update_state(task_id, state, meta)
        sse_publish_event(channel=self.sse_channel, type_=self._type,
                          state=state, meta=meta)
        logging.debug('Update State: {0} {1}'.format(state, meta))

    def _meta_exception_envelope(self, exc):
        """Create a envelope for exceptions.

        NOTE: workaround to be able to save the payload in celery in case of
        exceptions.
        """
        meta = dict(message=str(exc), payload=self._base_payload)
        return dict(
            exc_message=meta,
            exc_type=exc.__class__.__name__
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """When an error occurs, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            exception = self._meta_exception_envelope(exc=exc)
            self.update_state(task_id=task_id, state=FAILURE, meta=exception)
            self._update_record()
            logging.debug('Failure: {0}'.format(exception))

    def on_success(self, exc, task_id, *args, **kwargs):
        """When end correctly, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            meta = dict(message=str(exc), payload=self._base_payload)
            self.update_state(task_id=task_id, state=SUCCESS, meta=meta)
            self._update_record()
            logging.debug('Success: {0}'.format(meta))

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
            with celery_app.flask_app.app_context():
                handler()
        signal.signal(signal.SIGTERM, _handler)

    def set_base_payload(self, payload=None):
        """Set default base payload."""
        self._base_payload = {
            'deposit_id': self.deposit_id,
            'event_id': self.event_id,
            'sse_channel': self.sse_channel,
            'type': self._type,
        }
        if self.object:
            self._base_payload.update(
                tags=self.object.get_tags(),
                version_id=str(self.object.version_id)
            )
        if payload:
            self._base_payload.update(**payload)


class DownloadTask(AVCTask):
    """Download task."""

    def __init__(self):
        """Init."""
        self._type = 'file_download'

    @staticmethod
    def clean(version_id, *args, **kwargs):
        """Undo download task."""
        # Delete the file and the object version
        dispose_object_version(version_id)

    def run(self, uri, **kwargs):
        """Download file from a URL.

        :param self: reference to instance of task base class
        :param uri: URL of the file to download.
        """
        self._base_payload.update(key=self.object.key)

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

    format_keys = [
        'duration',
        'bit_rate',
        'size',
    ]
    stream_keys = [
        'avg_frame_rate',
        'codec_name',
        'codec_long_name',
        'width',
        'height',
        'nb_frames',
        'display_aspect_ratio',
        'color_range',
    ]

    _all_keys = format_keys + stream_keys

    def __init__(self):
        """Init."""
        self._type = 'file_video_metadata_extraction'

    def clean(self, deposit_id, version_id, *args, **kwargs):
        """Undo metadata extraction."""
        # 1. Revert patch on record
        recid = str(PersistentIdentifier.get(
            'depid', deposit_id).object_uuid)
        patch = [{
            'op': 'remove',
            'path': '/_cds/extracted_metadata',
        }]
        validator = 'cds.modules.records.validators.PartialDraft4Validator'
        try:
            patch_record(recid=recid, patch=patch, validator=validator)
        except jsonpatch.JsonPatchConflict as c:
            logger.warning(
                'Failed to apply JSON Patch to deposit {0}: {1}'.format(
                    recid, c))

    @classmethod
    def create_metadata_tags(cls, object_, keys, uri=None):
        """Extract metadata from the video and create corresponding tags."""
        uri = uri or replace_xrootd(object_.file.uri)
        # Extract video's metadata using `ff_probe`
        metadata = ff_probe_all(uri)
        extracted_dict = dict(metadata['format'], **metadata['streams'][0])
        # Add technical information to the ObjectVersion as Tags
        [ObjectVersionTag.create_or_update(object_, k, v)
         for k, v in extracted_dict.items()
         if k in keys]
        db.session.refresh(object_)
        return extracted_dict

    def run(self, uri=None, *args, **kwargs):
        """Extract metadata from given video file.

        All technical metadata, i.e. bitrate, will be translated into
        ``ObjectVersionTags``, plus all the metadata extracted will be
        store under ``_cds`` as ``extracted_metadata``.

        :param self: reference to instance of task base class
        :param uri: URL of the file to extract metadata from.
        """
        recid = str(PersistentIdentifier.get(
            'depid', self.deposit_id).object_uuid)

        self._base_payload.update(uri=uri)

        try:
            extracted_dict = self.create_metadata_tags(
                uri=uri, object_=self.object, keys=self._all_keys)
        except Exception as exc:
            db.session.rollback()
            raise self.retry(max_retries=5, countdown=5, exc=exc)

        tags = self.object.get_tags()

        db.session.commit()

        # Insert metadata into deposit's metadata
        patch = [{
            'op': 'add',
            'path': '/_cds/extracted_metadata',
            'value': extracted_dict
        }]
        validator = 'cds.modules.records.validators.PartialDraft4Validator'
        update_record.s(
            recid=recid, patch=patch, validator=validator).apply()

        # Update state
        self.update_state(
            state=SUCCESS,
            meta=dict(
                payload=dict(
                    tags=tags,
                    extracted_metadata=extracted_dict,),
                message='Attached video metadata'))


class ExtractFramesTask(AVCTask):
    """Extract frames task."""

    def __init__(self):
        """Init."""
        self._type = 'file_video_extract_frames'

    @staticmethod
    def clean(version_id, *args, **kwargs):
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
            .filter(tag_alias_2.key == 'context_type',
                    tag_alias_2.value.in_(['frame', 'frames-preview'])) \
            .all()
        # FIXME do a test for check separately every "undo" when
        # run a AVC workflow
        for slave in slaves:
            dispose_object_version(slave)

    def run(self, frames_start=5, frames_end=95, frames_gap=10,
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

        # Calculate time positions
        duration = float(self._base_payload['tags']['duration'])
        time_step = duration * frames_gap / 100
        start_time = duration * frames_start / 100
        end_time = (duration * frames_end / 100) + 0.01

        number_of_frames = ((frames_end - frames_start) / frames_gap) + 1

        def progress_updater(current_frame):
            """Progress reporter."""
            meta = dict(
                payload=dict(
                    size=duration,
                    percentage=current_frame / number_of_frames * 100, ),
                message='Extracting frames [{0} out of {1}]'.format(
                    current_frame, number_of_frames), )

            self.update_state(state=STARTED, meta=meta)

        try:
            # Generate frames
            ff_frames(input_file=replace_xrootd(self.object.file.uri),
                      start=start_time, end=end_time, step=time_step,
                      duration=duration, progress_callback=progress_updater,
                      output=os.path.join(output_folder, 'frame-{:d}.jpg'))
        except Exception as exc:
            db.session.rollback()
            shutil.rmtree(output_folder, ignore_errors=True)
            raise self.retry(max_retries=5, countdown=5, exc=exc)

        frames = sorted(
            os.listdir(output_folder),
            key=lambda f: int(f.rsplit('-', 1)[1].split('.', 1)[0]))

        [self._create_object(bucket=self.object.bucket, key=filename,
                             stream=open(in_output(filename), 'rb'),
                             size=os.path.getsize(in_output(filename)),
                             media_type='image', context_type='frame',
                             master_id=self.obj_id,
                             timestamp=start_time + (i + 1) * time_step)
         for i, filename in enumerate(frames)]

        # Generate GIF images
        self._create_gif(bucket=self.object.bucket, frames=frames,
                         output_dir=output_folder, master_id=self.obj_id)

        # Cleanup
        shutil.rmtree(output_folder)
        db.session.commit()

    @classmethod
    def _create_gif(cls, bucket, frames, output_dir, master_id):
        """Generate a gif image."""
        gif_filename = 'frames.gif'

        images = []
        for f in frames:
            image = Image.open(os.path.join(output_dir, f))
            # Convert image for better quality
            im = image.convert('RGB').convert(
                'P', palette=Image.ADAPTIVE, colors=255
            )
            images.append(im)
        gif_image = create_gif_from_frames(images)
        gif_fullpath = os.path.join(output_dir, gif_filename)
        gif_image.save(gif_fullpath, save_all=True)
        cls._create_object(bucket=bucket, key=gif_filename,
                           stream=open(gif_fullpath, 'rb'),
                           size=os.path.getsize(gif_fullpath),
                           media_type='image', context_type='frames-preview',
                           master_id=master_id)

    @classmethod
    def _create_object(cls, bucket, key, stream, size, media_type,
                       context_type, master_id, **tags):
        """Create object versions with given type and tags."""
        obj = ObjectVersion.create(
            bucket=bucket, key=key, stream=stream, size=size)
        ObjectVersionTag.create(obj, 'master', master_id)
        ObjectVersionTag.create(obj, 'media_type', media_type)
        ObjectVersionTag.create(obj, 'context_type', context_type)
        [ObjectVersionTag.create(obj, k, tags[k]) for k in tags]


class TranscodeVideoTask(AVCTask):
    """Transcode video task."""

    def __init__(self):
        """Init."""
        self._type = 'file_transcode'
        self._base_payload = {}  # {'type': self._type}

    def on_success(self, *args, **kwargs):
        """On success update the record if exists."""
        super(TranscodeVideoTask, self).on_success(*args, **kwargs)
        # update record if already published
        sync_records_with_deposit_files.s(
            deposit_id=self._base_payload['deposit_id']).apply_async()

    @staticmethod
    def _build_slave_key(preset_quality, master_key):
        """Build the object version key connected with the transcoding."""
        return 'slave_{0}.mp4'.format(preset_quality)

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
        folder = os.path.dirname(replace_xrootd(uri))
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
        self._base_payload.update(preset_quality=preset_quality)

        # Get master file's bucket_id
        bucket_id = self.object.bucket_id
        bucket_location = self.object.bucket.location.uri
        # Get master file's key
        master_key = self.object.key

        tags = self.object.get_tags()
        # Get master file's aspect ratio
        aspect_ratio = tags['display_aspect_ratio']
        # Get master file's width x height
        width = int(tags['width']) if 'width' in tags else None
        height = int(tags['height']) if 'height' in tags else None

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
            # XRootDPyFS doesn't implement root_path
            try:
                output_file = os.path.join(
                    directory.root_url + directory.base_path, filename)
            except AttributeError:
                output_file = os.path.join(directory.root_path, filename)

            try:
                # Start Sorenson
                job_id = start_encoding(input_file, output_file,
                                        preset_quality, aspect_ratio,
                                        max_height=height, max_width=width)
            except (InvalidResolutionError, TooHighResolutionError) as e:
                exception = self._meta_exception_envelope(exc=e)
                self.update_state(state=REVOKED, meta=exception)
                raise Ignore()

            # Set revoke handler, in case of an abrupt execution halt.
            self.set_revoke_handler(partial(stop_encoding, job_id))

            # Create ObjectVersionTags
            ObjectVersionTag.create(obj, 'master', self.obj_id)
            ObjectVersionTag.create(obj, '_sorenson_job_id', job_id)
            ObjectVersionTag.create(obj, 'preset_quality', preset_quality)
            ObjectVersionTag.create(obj, 'media_type', 'video')
            ObjectVersionTag.create(obj, 'context_type', 'subformat')
            preset_info = get_preset_info(aspect_ratio, preset_quality)
            for key, value in preset_info.items():
                ObjectVersionTag.create(obj, key, value)

            # Information necessary for monitoring
            job_info = dict(
                preset_quality=preset_quality,
                job_id=job_id,
                file_instance=str(file_instance.id),
                uri=output_file,
                version_id=str(obj.version_id),
                key=obj_key,
                tags=obj.get_tags(),
                percentage=0,
            )

        db.session.commit()

        self.update_state(
            state=STARTED,
            meta=dict(
                payload=dict(**job_info),
                message='Started transcoding.')
        )

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
                    message='{1} {0}'.format(status, percentage)))

            time.sleep(sleep_time)

        # Set file's location, if job has completed
        self._clean_file_name(output_file)
        with db.session.begin_nested():
            uri = output_file
            with file_opener_xrootd(uri, 'rb') as transcoded_file:
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


@shared_task(bind=True)
def sync_records_with_deposit_files(self, deposit_id, max_retries=5,
                                    countdown=5):
    """Low level files synchronize."""
    deposit_video = deposit_video_resolver(deposit_id)
    db.session.refresh(deposit_video.model)
    if deposit_video.is_published():
        try:
            # sync deposit files <--> record files
            deposit_video = deposit_video.edit().publish().commit()
            record_pid, record = deposit_video.fetch_published()
            # save changes
            deposit_video.commit()
            record.commit()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise self.retry(
                max_retries=max_retries, countdown=countdown, exc=exc)
        # index the record again
        _, record_video = deposit_video.fetch_published()
        RecordIndexer().index(record_video)


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
    old_status = deposit['_cds']['state']
    new_status = deposit._current_tasks_status()
    # create tasks status patch
    patches = jsonpatch.make_patch(old_status, new_status).patch
    # make it suitable for the deposit
    for patch in patches:
        patch['path'] = '/_cds/state{0}'.format(patch['path'])
    return patches


def spread_deposit_update(deposit=None, event_id=None, sse_channel=None):
    """If record is updated correctly, spread the news."""
    if deposit:
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
        RecordIndexer().bulk_index(iter([str(deposit.id)]))


def update_avc_deposit_state(deposit_id=None, event_id=None, sse_channel=None,
                             **kwargs):
    """Update deposit state on SSE and ElasticSearch."""
    if deposit_id:
        # get video
        video = deposit_video_resolver(deposit_id)
        # spread the news
        spread_deposit_update(deposit=video, event_id=str(event_id),
                              sse_channel=sse_channel),
        spread_deposit_update(deposit=video.project, event_id=str(event_id),
                              sse_channel=sse_channel)


def dispose_object_version(object_version):
    """Clean up resources related to an ObjectVersion."""
    if object_version:
        object_version = as_object_version(object_version)
        # remove the object version
        ObjectVersion.delete(
            bucket=object_version.bucket, key=object_version.key)
