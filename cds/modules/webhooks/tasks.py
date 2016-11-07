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


import requests
import json
from cds.modules.ffmpeg import ff_probe_all
from celery import current_app
from celery import shared_task, Task
from celery.states import FAILURE, STARTED, SUCCESS
from invenio_files_rest.models import as_object_version, ObjectVersionTag
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_sse import current_sse
from six import BytesIO
from sqlalchemy.orm.exc import ConcurrentModificationError


def _factory_sse_task_base(type_=None):
    """Build base celery task to send SSE messages upon status update.

    :param type_: Type of SSE message to send.
    :return: ``SSETask`` class.
    """

    class SSETask(Task):
        """Base class for tasks which might be sending SSE messages."""

        abstract = True

        def __init__(self):
            super(SSETask, self).__init__()
            self.default_payload = {}

        def __call__(self, *args, **kwargs):
            """Extract SSE channel from keyword arguments.

            .. note ::
                the channel is extracted from the ``sse_channel`` keyword
                argument.
            """
            self.sse_channel = kwargs.pop('sse_channel', None)
            with current_app.flask_app.app_context():
                return self.run(*args, **kwargs)

        def set_default_payload(self, **kwargs):
            self.default_payload = kwargs

        def _publish(self, state, meta):
            """Publish task's state to corresponding SSE channel."""
            if self.sse_channel:
                current_sse.publish(dict(state=state, meta=meta),
                                    type_=type_, channel=self.sse_channel)

        def update_state(self, state=None, payload=None, message=None):
            """Send SSE message on task's status updates."""
            payload.update(self.default_payload)
            meta = dict(message=message, payload=payload)
            super(SSETask, self).update_state(state=state, meta=meta)
            self._publish(state, meta)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            """When an error occurs, attach useful information to the state."""
            meta = dict(message=str(exc), payload=self.default_payload)
            self._publish(state=FAILURE, meta=meta)

    return SSETask


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_download'))
def download_to_object_version(self, url, object_version, **kwargs):
    r"""Download file from a URL.

    :param url: URL of the file to download.
    :param object_version: ``ObjectVersion`` instance or object version id.
    :param chunk_size: Size of the chunks for downloading.
    :param \**kwargs:
    """
    self.set_default_payload(object_version=object_version, url=url, **kwargs)

    with db.session.begin_nested():
        object_version = as_object_version(object_version)

        # Make HTTP request
        response = requests.get(url, stream=True)

        def progress_updater(size, total):
            """Progress reporter."""
            self.update_state(
                state=STARTED,
                payload=dict(
                    key=object_version.key,
                    version_id=str(object_version.version_id),
                    size=total,
                    tags=object_version.get_tags(),
                    percentage=size or 0.0 / total * 100,
                ),
                message='Downloading {0} of {1}'.format(size, total)
            )

        object_version.set_contents(
            BytesIO(response.content), progress_callback=progress_updater)

    db.session.commit()

    # Return downloaded file location
    return str(object_version.version_id)


@shared_task(
    bind=True,
    base=_factory_sse_task_base(type_='file_video_metadata_extraction'))
def video_metadata_extraction(self, uri, object_version=None, deposit_id=None,
                              **kwargs):
    """Extract metadata from given video file.

    All technical metadata, i.e. bitrate, will be translated into
    ``ObjectVersionTags``, plus all the metadata extracted will be store under
    ``_deposit`` as ``extracted_metadta``.

    :param uri: the video's URI
    :param object_version: the object version that contains the actual video
    :param deposit_id: the ID of the deposit
    """
    self.set_default_payload(object_version=object_version, uri=uri, **kwargs)

    object_version = as_object_version(object_version)
    recid = PersistentIdentifier.get('depid', deposit_id).object_uuid

    # Extract video's metadata using `ff_probe`
    metadata = json.loads(ff_probe_all(uri))

    # Add technical information to the ObjectVersion as Tags
    format_keys = ['duration', 'bit_rate', 'filename', 'size']
    stream_keys = ['avg_frame_rate', 'codec_name', 'width', 'height',
                   'nb_frames', 'display_aspect_ratio', 'color_range']

    [ObjectVersionTag.create(object_version, key, section[key])
     for section, keys in [(metadata['format'], format_keys),
                           (metadata['streams'][0], stream_keys)]
     for key in keys
     if key in section]

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
        payload=dict(
            key=object_version.key,
            version_id=str(object_version.version_id),
            tags=object_version.get_tags(),
            deposit_id=deposit_id,
        ),
        message='Attached video metadata')


@shared_task(
    bind=True, base=_factory_sse_task_base(type_='file_video_extract_frames'))
def video_extract_frames(self, object_version, start=5, end=95, gap=10):
    """Extract images from some frames of the video.

    Each of the frame images generates an ``ObjectVersion`` tagged as "frame"
    using ``ObjectVersionTags``.

    :param object_version: Master video to extract frames from.
    :param start: Start percentage, default 5%.
    :param end: End percentage, defatul 95%.
    :param gap: Percentage between frames from start to end, default 10%.
    """
    pass


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_trancode'))
def video_transcode(self, object_version, presets=None):
    """Launch video transcoding.

    For each of the presents generate a new ``ObjectVersion`` tagged as slave
    with the preset name as key and a link to the master version.

    :param object_version: Master video.
    :param presets: List of presets to use for transcoding. If ``None`` it will
        use the default values set in ``VIDEO_DEFAULT_PRESETS``.
    """
    pass


@shared_task(bind=True)
def update_record(self, recid, patch, max_retries=10, countdown=5):
    """Update a given record with a patch.

    :param recid: the ID of the record
    :param patch: the patch operation to apply
    :param max_retries: times to retry operation
    :param countdown: time to sleep between retries
    """
    try:
        record = Record.get_record(recid)
        record = record.patch(patch)
        record.commit()
        db.session.commit()
    except ConcurrentModificationError as exc:
        db.session.rollback()
        self.retry(max_retries=max_retries, countdown=countdown, exc=exc)
