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

import hashlib
import json
import os
import shutil
import signal
import tempfile
import time
from collections import deque

import requests
from cds_sorenson.api import get_encoding_status, start_encoding, stop_encoding
from celery import Task, shared_task, current_app as celery_app
from celery.states import FAILURE, STARTED, SUCCESS
from flask import current_app
from invenio_db import db
from invenio_files_rest.models import (FileInstance, ObjectVersion,
                                       ObjectVersionTag, as_object_version)
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_sse import current_sse
from six import BytesIO
from sqlalchemy.orm.exc import ConcurrentModificationError

from ..ffmpeg import ff_frames, ff_probe_all


def _factory_sse_task_base(type_=None):
    """Build base celery task to send SSE messages upon status update.

    :param type_: Type of SSE message to send.
    :return: ``SSETask`` class.
    """
    class SSETask(Task):
        """Base class for tasks which might be sending SSE messages."""

        abstract = True

        def __init__(self):
            """."""
            super(SSETask, self).__init__()
            self._base_payload = {}

        def __call__(self, *args, **kwargs):
            """Extract SSE channel from keyword arguments.

            .. note ::
                the channel is extracted from the ``sse_channel`` keyword
                argument.
            """
            self.sse_channel = kwargs.pop('sse_channel', None)
            with self.app.flask_app.app_context():
                return self.run(*args, **kwargs)

        def _publish(self, state, meta):
            """Publish task's state to corresponding SSE channel."""
            if self.sse_channel:
                data = {'state': state, 'meta': meta}
                current_sse.publish(
                    data=data, type_=type_, channel=self.sse_channel)

        def update_state(self, task_id=None, state=None, meta=None):
            """."""
            self._base_payload.update(meta.get('payload', {}))
            meta['payload'] = self._base_payload
            super(SSETask, self).update_state(task_id, state, meta)
            self._publish(state=state, meta=meta)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            """When an error occurs, attach useful information to the state."""
            with celery_app.flask_app.app_context():
                meta = dict(message=str(exc), payload=self._base_payload)
                self._publish(state=FAILURE, meta=meta)

        def on_success(self, exc, *args, **kwargs):
            """When end correctly, attach useful information to the state."""
            with celery_app.flask_app.app_context():
                meta = dict(message=str(exc), payload=self._base_payload)
                self._publish(state=SUCCESS, meta=meta)

    return SSETask


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_download'))
def download_to_object_version(self, uri, object_version, **kwargs):
    r"""Download file from a URL.

    :param uri: URL of the file to download.
    :param object_version: ``ObjectVersion`` instance or object version id.
    :param chunk_size: Size of the chunks for downloading.
    :param \**kwargs:
    """
    object_version = as_object_version(object_version)

    self._base_payload = dict(
        key=object_version.key,
        version_id=str(object_version.version_id),
        tags=object_version.get_tags(),
        event_id=kwargs.get('event_id', None),
        deposit_id=kwargs.get('deposit_id', None), )

    # Make HTTP request
    response = requests.get(uri, stream=True)

    if 'Content-Length' in response.headers:
        headers_size = int(response.headers.get('Content-Length'))
    else:
        headers_size = 0

    def progress_updater(size, total):
        """Progress reporter."""
        size = size or headers_size
        meta = dict(
            payload=dict(
                size=size,
                total=total,
                percentage=total * 100 / size, ),
            message='Downloading {0} of {1}'.format(total, size),
        )

        self.update_state(state=STARTED, meta=meta)

    object_version.set_contents(
        BytesIO(response.content), progress_callback=progress_updater)

    db.session.commit()

    return str(object_version.version_id)


@shared_task(
    bind=True,
    base=_factory_sse_task_base(type_='file_video_metadata_extraction'))
def video_metadata_extraction(self, uri, object_version, deposit_id,
                              *args, **kwargs):
    """Extract metadata from given video file.

    All technical metadata, i.e. bitrate, will be translated into
    ``ObjectVersionTags``, plus all the metadata extracted will be store under
    ``_deposit`` as ``extracted_metadta``.

    :param uri: the video's URI
    :param object_version: the object version that (will) contain the actual
           video
    :param deposit_id: the ID od the deposit
    """
    object_version = as_object_version(object_version)

    self._base_payload = dict(
        object_version=str(object_version.version_id),
        uri=uri,
        tags=object_version.get_tags(),
        deposit_id=deposit_id,
        event_id=kwargs.get('event_id', None), )

    recid = PersistentIdentifier.get('depid', deposit_id).object_uuid

    # Extract video's metadata using `ff_probe`
    metadata = json.loads(ff_probe_all(uri))

    # Add technical information to the ObjectVersion as Tags
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

    [ObjectVersionTag.create(object_version, k, v)
     for k, v in dict(metadata['format'], **metadata['streams'][0]).items()
     if k in (format_keys + stream_keys)]

    db.session.commit()

    # Insert metadata into deposit's metadata
    patch = [{
        'op': 'add',
        'path': '/_deposit/extracted_metadata',
        'value': metadata
    }]
    result = update_record.s(recid, patch).apply_async()
    result.get()

    # Update state
    self.update_state(
        state=SUCCESS,
        meta=dict(
            payload=dict(
                tags=object_version.get_tags(), ),
            message='Attached video metadata'))


@shared_task(
    bind=True, base=_factory_sse_task_base(type_='file_video_extract_frames'))
def video_extract_frames(self,
                         object_version,
                         frames_start=5,
                         frames_end=95,
                         frames_gap=1,
                         **kwargs):
    """Extract images from some frames of the video.

    Each of the frame images generates an ``ObjectVersion`` tagged as "frame"
    using ``ObjectVersionTags``.

    :param object_version: master video to extract frames from.
    :param frames_start: start percentage, default 5.
    :param frames_end: end percentage, default 95.
    :param frames_gap: percentage between frames from start to end, default 10.
    """
    object_version = as_object_version(object_version)

    self._base_payload = dict()

    input_file = object_version.file.uri
    output_folder = tempfile.mkdtemp()

    def progress_updater(seconds, duration):
        """Progress reporter."""
        meta = dict(
            payload=dict(
                size=duration,
                percentage=seconds or 0.0 / duration * 100, ),
            message='Extracting frames {0} of {1} seconds'.format(seconds, duration), )

        self.update_state(state=STARTED, meta=meta)

    ff_frames(
        object_version.file.uri,
        frames_start,
        frames_end,
        frames_gap,
        os.path.join(output_folder, 'frame-%d.jpg'),
        progress_callback=progress_updater)

    for filename in os.listdir(output_folder):
        obj = ObjectVersion.create(
            bucket=object_version.bucket,
            key=filename,
            stream=open(os.path.join(output_folder, filename),'rb'))
        ObjectVersionTag.create(obj, 'master', object_version.version_id)

    shutil.rmtree(output_folder)
    db.session.commit()


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_trancode'))
def video_transcode(self,
                    object_version,
                    video_presets=None,
                    sleep_time=5,
                    **kwargs):
    """Launch video transcoding.

    For each of the presets generate a new ``ObjectVersion`` tagged as slave
    with the preset name as key and a link to the master version.

    :param object_version: Master video.
    :param video_presets: List of presets to use for transcoding. If ``None``
        it will use the default values set in ``VIDEO_DEFAULT_PRESETS``.
    :param sleep_time: the time interval between requests for Sorenson status
    """
    object_version = as_object_version(object_version)

    self._base_payload = dict(
        object_version=str(object_version.version_id),
        video_presets=video_presets,
        tags=object_version.get_tags(),
        deposit_id=kwargs.get('deposit_id', None),
        event_id=kwargs.get('event_id', None),
    )

    job_ids = deque()
    # Set handler for canceling all jobs
    def handler(signum, frame):
        map(lambda _info: stop_encoding(info['job_id']), job_ids)
    signal.signal(signal.SIGTERM, handler)

    # Get master file's bucket_id
    bucket_id = object_version.bucket_id
    bucket_location = object_version.bucket.location.uri

    preset_config = current_app.config['CDS_SORENSON_PRESETS']
    for preset in video_presets or preset_config.keys():
        # Create FileInstance and get generated UUID
        file_instance = FileInstance.create()
        # Create ObjectVersion
        base_name = object_version.key.rsplit('.', 1)[0]
        new_extension = preset_config[preset][1]
        obj = ObjectVersion.create(
            bucket=bucket_id,
            key='{0}-{1}{2}'.format(base_name, preset, new_extension)
        )
        obj.set_file(file_instance)
        ObjectVersionTag.create(obj, 'master', str(object_version.version_id))
        ObjectVersionTag.create(obj, 'preset', preset)

        # Extract new location
        storage = file_instance.storage(default_location=bucket_location)
        directory, filename = storage._get_fs()

        # Start Sorenson
        input_file = object_version.file.uri
        output_file = os.path.join(directory.root_path, filename)

        job_id = start_encoding(input_file, preset, output_file)
        ObjectVersionTag.create(obj, '_sorenson_job_id', job_id)
        self.update_state(
            state=STARTED,
            meta=dict(
                payload=dict(preset=preset, job_id=job_id),
                message='Started transcoding.'
            )
        )

        job_ids.append(dict(
            preset=preset, job_id=job_id,
            file_instance=file_instance, uri=output_file
        ))

    # Monitor jobs and report accordingly
    while job_ids:
        info = job_ids.popleft()

        # Get job status
        status = get_encoding_status(info['job_id'])['Status']
        percentage = 100 if status['TimeFinished'] else status['Progress']

        # Update task's state for each individual preset
        self.update_state(
            state=STARTED,
            meta=dict(
                payload=dict(
                    preset=info['preset'],
                    job_id=info['job_id'],
                    percentage=percentage,
                ),
                message='Transcoding {0}'.format(percentage),
            )
        )

        # Set file's location for completed jobs
        if percentage == 100:
            uri = info['uri']
            with open(uri, 'rb') as transcoded_file:
                digest = hashlib.md5(transcoded_file.read()).hexdigest()
            size = os.path.getsize(uri)
            checksum = '{0}:{1}'.format('md5', digest)
            info['file_instance'].set_uri(uri, size, checksum)
        else:
            job_ids.append(info)

        time.sleep(sleep_time)

    # Commit changes
    db.session.commit()


@shared_task(bind=True)
def update_record(self, recid, patch, max_retries=5, countdown=5):
    """Update a given record with a patch.

    Retries ``max_retries`` after ``countdown`` seconds.

    :param recid: the UUID of the record
    :param patch: the patch operation to apply
    :param max_retries: times to retry operation
    :param countdown: time to sleep between retries
    """
    try:
        with db.session.begin_nested():
            # FIXME
            from sqlalchemy.orm.exc import DetachedInstanceError
            from flask_security import current_user
            try:
                current_user.id
            except DetachedInstanceError:
                db.session.add(current_user)
            except AttributeError:
                pass
            # /FIXME
            record = Record.get_record(recid)
            record = record.patch(patch)
            #  db.session.refresh(record.model)
            record.commit()
        db.session.commit()
    except ConcurrentModificationError as exc:
        db.session.rollback()
        self.retry(max_retries=max_retries, countdown=countdown, exc=exc)
