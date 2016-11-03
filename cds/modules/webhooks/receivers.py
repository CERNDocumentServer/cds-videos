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
"""Webhook Receivers"""

from __future__ import absolute_import

from celery import chain, group
from flask import url_for
from invenio_db import db
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified

from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)

from .tasks import (download_to_object_version, video_extract_frames,
                    video_metadata_extraction, video_transcode)


class CeleryAsyncReceiver(Receiver):
    """TODO."""

    def status(self, event):
        """TODO."""

    def delete(self, event):
        """TODO."""
        pass


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    def run(self, event):
        """Create object version and send celery task to download.

        Mandatory fields in the payload:
          * uri, location to download the viewo.
          * bucket_id
          * key, file name.
          * deposit_id

        Optional:
          * sse_channel, if set all the tasks will publish their status update
            to it.

        For more info see the task
        :func: `~cds.modules.webhooks.tasks.download_to_object_version` this
        receiver is using.
        """
        assert 'bucket_id' in event.payload
        assert 'uri' in event.payload
        assert 'key' in event.payload
        assert 'deposit_id' in event.payload

        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])

            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', str(event.id))
            db.session.expunge(event)
        db.session.commit()

        task = download_to_object_version.s(event.payload['uri'],
                                            str(object_version.version_id),
                                            event_id=str(event.id),
                                            **event.payload).apply_async()

        with db.session.begin_nested():
            object_version = as_object_version(object_version.version_id)
            event.response = dict(
                _tasks=task.as_tuple(),
                links=dict(),
                key=object_version.key,
                version_id=str(object_version.version_id),
                tags=object_version.get_tags(), )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
            db.session.add(event)
        db.session.commit()


class AVCWorkflow(CeleryAsyncReceiver):
    """AVC workflow receiver."""

    def run(self, event):
        """Run AVC workflow for video transcoding.

        Steps:
          * Download the video file (if not done yet).
          * Extract metadata from the video.
          * Run video transcoding.
          * Extract frames from the video.

        Mandatory fields in the payload:
          * uri, if the video needs to be downloaded.
          * bucket_id, only if URI is provided.
          * key, only if URI is provided.
          * version_id, if the video has been downloaded via HTTP (the previous
            fields are not needed in this case).
          * deposit_id

        Optional:
          * sse_channel, if set all the tasks will publish their status update
            to it.
          * video_presets, if not set the default presets will be used.
          * frames_start, if not set the default value will be used.
          * frames_end, if not set the default value will be used.
          * frames_gap, if not set the default value will be used.

        For more info see the tasks used in the workflow:
          * :func: `~cds.modules.webhooks.tasks.download_to_object_version`
          * :func: `~cds.modules.webhooks.tasks.video_metadata_extraction`
          * :func: `~cds.modules.webhooks.tasks.video_extract_frames`
          * :func: `~cds.modules.webhooks.tasks.video_transcode`
        """
        assert ('uri' in event.payload and 'bucket_id' in event.payload and
                'key' in event.payload) or ('version_id' in event.payload)
        assert 'deposit_id' in event.payload

        with db.session.begin_nested():
            if 'version_id' in event.payload:
                object_version = as_object_version(event.payload['version_id'])
                first_step = video_metadata_extraction.si(
                    object_version.file.uri,
                    str(object_version.version_id),
                    event.payload['deposit_id'])
            else:
                object_version = ObjectVersion.create(
                    bucket=event.payload['bucket_id'],
                    key=event.payload['key'])
                ObjectVersionTag.create(object_version, 'uri_origin',
                                        event.payload['uri'])
                first_step = group(
                    download_to_object_version.si(
                        event.payload['url'],
                        str(object_version.version_id),
                        event_id=event.id,
                        **event.payload),
                    video_metadata_extraction.si(
                        event.payload['uri'],
                        str(object_version.version_id),
                        event_id=event.id,
                        **event.payload), )

            ObjectVersionTag.create(object_version, '_event_id', event.id)

            tasks = chain(
                first_step,
                group(
                    video_transcode.si(str(object_version.version_id),
                                       event_id=event.id,
                                       **event.payload),
                    video_extract_frames.si(str(object_version.version_id),
                                            event_id=event.id,
                                            **event.payload), ),
            ).apply_async()

            event.response = dict(
                _tasks=tasks.as_tuple(),
                links=dict(),
                key=object_version.key,
                version_id=object_version.versrion_id,
                tags=object_version.get_tags(), )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
