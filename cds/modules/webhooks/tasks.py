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
from cds.modules.ffmpeg import ff_frames, ff_probe, ff_probe_all
from celery import shared_task, Task
from celery.states import STARTED
from invenio_files_rest.models import as_object_version
from invenio_db import db
from invenio_sse import current_sse
from six import BytesIO


def _factory_sse_task_base(type_=None):
    """Build base celery task to send SSE messages upon status update.

    :param type_: Type of SSE message to send.
    :return: ``SSETask`` class.
    """

    class SSETask(Task):
        """Base class for tasks which might be sending SSE messages."""

        abstract = True

        def __call__(self, *args, **kwargs):
            """Extract SSE channel from keyword arguments.

            .. note ::
                the channel is extracted from the ``sse_channel`` keyword
                argument.
            """
            self.sse_channel = kwargs.pop('sse_channel', None)
            return self.run(*args, **kwargs)

        def update_state(self, task_id=None, state=None, meta=None):
            """."""
            super(SSETask, self).update_state(task_id, state, meta)
            if self.sse_channel:
                data = dict(state=state, meta=meta)
                current_sse.publish(
                    data, type_=type_, channel=self.sse_channel)

    return SSETask


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_download'))
def download_to_object_version(self, url, object_version, **kwargs):
    r"""Download file from a URL.

    :param url: URL of the file to download.
    :param object_version: ``ObjectVersion`` instance or object version id.
    :param chunk_size: Size of the chunks for downloading.
    :param \**kwargs:
    """
    with db.session.begin_nested():
        object_version = as_object_version(object_version)

        # Make HTTP request
        response = requests.get(url, stream=True)

        def progress_updater(size, total):
            """Progress reporter."""
            meta = dict(
                payload=dict(
                    key=object_version.key,
                    version_id=str(object_version.version_id),
                    size=total,
                    tags=object_version.get_tags(),
                    percentage=size or 0.0 / total * 100,
                    deposit_id=kwargs.get('deposit_id', None), ),
                envent_id=kwargs.get('event_id', None),
                message='Downloading {0} of {1}'.format(size, total), )

            self.update_state(state=STARTED, meta=meta)

        object_version.set_contents(
            BytesIO(response.content), progress_callback=progress_updater)

    db.session.commit()

    # Return downloaded file location
    return str(object_version.version_id)


@shared_task(
    bind=True,
    base=_factory_sse_task_base(type_='file_video_metadata_extraction'))
def video_metadata_extraction(self, uri, object_version=None, record_id=None):
    """Extract metadata from given video file.

    All technical metadata, i.e. bitrate, will be translated into
    ``ObjectVersionTags``, plus all the metadata extracted will be store under
    ``_deposit`` as ``extracted_metadta``.

    :param uri:
    :param object_version:
    :param record_id:
    """
    info = json.loads(ff_probe_all(uri))
    # extract technical metadata and added to the ObjectVersion as Tags

    # create patch to update `_deposit/extracted_metadata`
    patch = None
    update_record.apply_async(record_id, patch)


@shared_task(
    bind=True, base=_factory_sse_task_base(type_='file_video_extract_frames'))
def video_extract_frames(self, object_version, start=5, end=95, gap=10):
    """Extract images from some frames of the video.

    Each of the frame images generates an ``ObjectVersion`` tagged as "frame"
    using ``ObjectVersionTags``.

    :param object_version: master video to extract frames from.
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


@shared_task()
def update_record(recid, patch, try_times=5, countdown=5):
    """Update a given record with a patch.

    Retries ``try_times`` after ``countdown`` seconds.

    :param recid:
    :param patch:
    :param try_times:
    :param countdown:
    """
    pass
