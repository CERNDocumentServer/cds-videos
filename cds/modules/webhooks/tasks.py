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

    :param uri:
    :param object_version:
    :param record_id:
    """


@shared_task(bind=True, base=_factory_sse_task_base(type_='file_trancode'))
def transcode(self, object_version):
    """."""
