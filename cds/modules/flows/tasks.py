# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2018, 2020 CERN.
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

import json
import logging
import os
import shutil
import signal
import tempfile
from functools import partial

import jsonpatch
import requests
from celery import Task as _Task
from celery import current_app as celery_app
from celery import shared_task
from flask import current_app

from .deposit import update_deposit_state
from celery.states import FAILURE, STARTED, SUCCESS
from celery.result import AsyncResult
from celery.task.control import revoke
from celery.utils.log import get_task_logger
from flask_iiif.utils import create_gif_from_frames
from invenio_db import db
from invenio_files_rest.models import (ObjectVersion,
                                       ObjectVersionTag, as_bucket,
                                       as_object_version)
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from PIL import Image
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import ConcurrentModificationError
from werkzeug.utils import import_string


from ..ffmpeg import ff_frames, ff_probe_all
from ..records.utils import to_string
from ..opencast.api import start_workflow
from ..opencast.utils import get_qualities
from ..xrootd.utils import file_opener_xrootd
from .files import move_file_into_local, dispose_object_version
from .models import as_task

from cds.modules.flows.models import TaskMetadata, Status

logger = get_task_logger(__name__)


class CeleryTask(_Task):
    """The task class which is used as the minimal unit of work.

    This class is a wrapper around ``celery.Task``
    """

    def commit_status(self, task_id, state=Status.PENDING, message=''):
        """Commit task status to the database."""
        with celery_app.flask_app.app_context():
            task = self.get_task(task_id)
            task.status = state
            task.message = message
            db.session.merge(task)
            db.session.commit()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Update task status on database."""
        task_id = kwargs.get('task_id', task_id)
        self.commit_status(task_id, Status.FAILURE, str(einfo))
        super(CeleryTask, self).on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Update tasks status on database."""
        task_id = kwargs.get('task_id', task_id)
        self.commit_status(
            task_id,
            Status.SUCCESS,
            '{}'.format(retval),
        )
        super(CeleryTask, self).on_success(retval, task_id, args, kwargs)

    @staticmethod
    def get_status(task_id):
        """Get singular task status."""
        task = CeleryTask.get_task(task_id)
        return {'status': str(task.status), 'message': task.message}

    @staticmethod
    def get_task(task_id):
        """Get singular task from database."""
        try:
            task = as_task(task_id)
            return task
        except Exception:
            raise KeyError('Task ID %s not found', task_id)

    @staticmethod
    def stop_task(task_id):
        """Stop singular task."""
        task = CeleryTask.get_task(task_id)

        if task.status == Status.PENDING:
            revoke(str(task.id), terminate=True, signal='SIGKILL')
            result = AsyncResult(str(task.id))
            result.forget()

    @staticmethod
    def restart_task(task_id, flow_id, flow_payload):
        """Restart singular task."""
        task = CeleryTask.get_task(task_id)

        # self.stop_task(task)
        # If a task gets send to the queue with the same id, it gets
        # automagically restarted, no need to stop it.

        task.status = Status.PENDING
        db.session.add(task)

        kwargs = {'flow_id': flow_id, 'task_id': str(task.id)}
        kwargs.update(task.payload)
        kwargs.update(flow_payload)
        return (
            celery_app.tasks.get(task.name).subtask(
                task_id=str(task.id),
                kwargs=kwargs,
                immutable=True,
            ).apply_async()
        )


class AVCTask(CeleryTask):
    """Base class for tasks."""

    abstract = True

    @property
    def name(self):
        return '.'.join([self.__module__, self.__name__])

    def _extract_call_arguments(self, arg_list, **kwargs):
        for name in arg_list:
            setattr(self, name, kwargs.pop(name, None))
        return kwargs

    def __call__(self, *args, **kwargs):
        """Extract keyword arguments."""
        arg_list = ['flow_id', 'deposit_id', 'key']
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
        super(AVCTask, self).on_failure(
            exc=exc, task_id=task_id, args=args, kwargs=kwargs, einfo=einfo)

    def on_success(self, exc, task_id, args, kwargs):
        """When end correctly, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            meta = dict(message=str(exc), payload=self._base_payload)
            self.update_state(task_id=task_id, state=SUCCESS, meta=meta)
            self._update_record()
            logging.debug('Success: {0}'.format(meta))
        super(AVCTask, self).on_success(
            retval=exc, task_id=task_id, args=args, kwargs=kwargs)

    def _update_record(self):
        # update record state
        with celery_app.flask_app.app_context():
            deposit_id = self._base_payload.get('deposit_id')
            if deposit_id:
                update_deposit_state(
                    deposit_id=self._base_payload.get('deposit_id'))

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
            'flow_id': self.flow_id,
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
        if version_id:
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
                'Failed to apply JSON Patch to deposit %s: %s', recid, c
            )

        # Delete tmp file if any
        obj = as_object_version(version_id)
        temp_location = obj.get_tags().get('temp_location', None)
        if temp_location:
            shutil.rmtree(temp_location)
            ObjectVersionTag.delete(obj, 'temp_location')
            db.session.commit()

    @classmethod
    def get_metadata_tags(cls, object_=None, uri=None):
        """Get metadata tags."""
        # Extract video's metadata using `ff_probe`
        if uri:
            metadata = ff_probe_all(uri)
        else:
            with move_file_into_local(object_) as url:
                metadata = ff_probe_all(url)
        return dict(metadata['format'], **metadata['streams'][0])

    @classmethod
    def create_metadata_tags(cls, object_, keys, uri=None):
        """Extract metadata from the video and create corresponding tags."""

        extracted_dict = cls.get_metadata_tags(object_=object_, uri=uri)
        # Add technical information to the ObjectVersion as Tags
        [ObjectVersionTag.create_or_update(object_, k, to_string(v))
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
        """
        recid = str(PersistentIdentifier.get(
            'depid', self.deposit_id).object_uuid)

        self._base_payload.update(uri=uri)

        try:
            extracted_dict = self.create_metadata_tags(
                uri=uri, object_=self.object, keys=self._all_keys)
        except Exception:
            db.session.rollback()
            raise

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

        return json.dumps(extracted_dict)


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

        # Remove temporary directory on abrupt execution halts.
        self.set_revoke_handler(lambda: shutil.rmtree(output_folder,
                                                      ignore_errors=True))

        # Calculate time positions
        options = self._time_position(
            duration=self._base_payload['tags']['duration'],
            frames_start=frames_start, frames_end=frames_end,
            frames_gap=frames_gap
        )

        def progress_updater(current_frame):
            """Progress reporter."""
            percentage = current_frame / options['number_of_frames'] * 100
            meta = dict(
                payload=dict(
                    size=options['duration'],
                    percentage=percentage
                ),
                message='Extracting frames [{0} out of {1}]'.format(
                    current_frame, options['number_of_frames']),
            )
            logging.debug(meta['message'])
            self.update_state(state=STARTED, meta=meta)

        try:
            frames = self._create_frames(frames=self._create_tmp_frames(
                object_=self.object,
                output_dir=output_folder,
                progress_updater=progress_updater, **options
            ), object_=self.object, **options)
        except Exception:
            db.session.rollback()
            shutil.rmtree(output_folder, ignore_errors=True)
            self.clean(version_id=self.obj_id)
            raise
        # Generate GIF images
        self._create_gif(bucket=str(self.object.bucket.id), frames=frames,
                         output_dir=output_folder, master_id=self.obj_id)

        # Cleanup
        shutil.rmtree(output_folder)
        db.session.commit()

    @classmethod
    def _time_position(cls, duration, frames_start=5, frames_end=95,
                       frames_gap=10):
        """Calculate time positions."""
        duration = float(duration)
        time_step = duration * frames_gap / 100
        start_time = duration * frames_start / 100
        end_time = (duration * frames_end / 100) + 0.01

        number_of_frames = ((frames_end - frames_start) / frames_gap) + 1

        return {
            'duration': duration, 'start_time': start_time,
            'end_time': end_time, 'time_step': time_step,
            'number_of_frames': number_of_frames,
        }

    @classmethod
    def _create_tmp_frames(cls, object_, start_time, end_time, time_step,
                           duration, output_dir, progress_updater=None,
                           **kwargs):
        """Create frames in temporary files."""
        # Generate frames
        with move_file_into_local(object_) as url:
            ff_frames(input_file=url,
                      start=start_time, end=end_time, step=time_step,
                      duration=duration, progress_callback=progress_updater,
                      output=os.path.join(output_dir, 'frame-{:d}.jpg'))
        # sort them
        sorted_ff_frames = sorted(
            os.listdir(output_dir),
            key=lambda f: int(f.rsplit('-', 1)[1].split('.', 1)[0]))
        # return full path
        return [os.path.join(output_dir, path) for path in sorted_ff_frames]

    @classmethod
    def _create_frames(cls, frames, object_, start_time, time_step, **kwargs):
        """Create frames."""

        [cls._create_object(
            bucket=object_.bucket, key=os.path.basename(filename),
            stream=file_opener_xrootd(filename, 'rb'),
            size=os.path.getsize(filename),
            media_type='image', context_type='frame',
            master_id=object_.version_id,
            timestamp=start_time + (i + 1) * time_step)
         for i, filename in enumerate(frames)]

        return frames

    @classmethod
    def _create_gif(cls, bucket, frames, output_dir, master_id):
        """Generate a gif image."""
        gif_filename = 'frames.gif'
        bucket = as_bucket(bucket)

        images = []
        for f in frames:
            image = Image.open(file_opener_xrootd(f, 'rb'))
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
        ObjectVersionTag.create(obj, 'master', str(master_id))
        ObjectVersionTag.create(obj, 'media_type', media_type)
        ObjectVersionTag.create(obj, 'context_type', context_type)
        [ObjectVersionTag.create(obj, k, to_string(tags[k])) for k in tags]


class TranscodeVideoTask(AVCTask):
    """Transcode video task."""

    def __init__(self):
        """Init."""
        self._type = 'file_transcode'
        self._base_payload = {}  # {'type': self._type}

    def on_success(self, *args, **kwargs):
        """Override on success."""
        pass

    def on_failure(self, *args, **kwargs):
        """Override on failure."""
        pass

    @staticmethod
    def _build_subformat_key(preset_quality):
        """Build the object version key connected with the transcoding."""
        return '{0}.mp4'.format(preset_quality)

    def clean(self, version_id, *args, **kwargs):
        """Delete generated ObjectVersion slaves."""
        object_version = as_object_version(version_id)
        if object_version:
            dispose_object_version(object_version)

    def run(self, *args, **kwargs):
        """Launch video transcoding.

        Create one Task for every quality.

        :param self: reference to instance of task base class
        """

        tags = self.object.get_tags()
        # Get master file's width x height
        width = int(tags['width']) if 'width' in tags else None
        height = int(tags['height']) if 'height' in tags else None
        # Get master file's aspect ratio
        aspect_ratio = tags['display_aspect_ratio']

        qualities = get_qualities(video_height=height, video_width=width)

        # Start Opencast transcoding
        event_id = start_workflow(
            self.object,
            qualities,
        )

        # Set revoke handler, in case of an abrupt execution halt.
        # TODO: TO be updated to opencast
        # self.set_revoke_handler(partial(sorenson.stop_encoding, event_id))
        ObjectVersionTag.create(self.object, '_opencast_event_id', event_id)
        # for key, value in preset_config.items():
        #     ObjectVersionTag.create(obj, key, value)
        # Information necessary for monitoring
        job_info = dict(
            opencast_event_id=event_id,
            version_id=str(self.object.version_id),
            key=self.object.key,
            tags=self.object.get_tags(),
        )

        for quality in qualities:
            task = TaskMetadata.create(
                flow_id=self.object.get_tags()['_flow_id'],
                name="file_transcode",
                payload=kwargs,
            )
            task.status = Status.STARTED
            task.message = "Started transcoding."
            task_payload = task.payload.copy()
            task_payload.update(quality=quality, **job_info)
            task_payload.update(
                opencast_publication_tag=
                current_app.config['CDS_OPENCAST_QUALITIES'][quality][
                    "opencast_publication_tag"]
            )
            task.payload = task_payload
            db.session.commit()

        return job_info['version_id']


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
    from cds.modules.deposit.api import deposit_video_resolver
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
