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

"""Webhook Receivers."""

from __future__ import absolute_import

from celery import chain, group
from flask import current_app
from invenio_db import db
from celery import states
from flask import url_for
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified
from celery.result import result_from_tuple
import json

from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)

from .status import ComputeGlobalStatus, iterate_result, collect_info
from .tasks import (download_to_object_version, video_extract_frames,
                    video_metadata_extraction, video_transcode,
                    update_deposit_state)


class CeleryAsyncReceiver(Receiver):
    """Celery Async Receiver abstract class."""

    CELERY_STATES_TO_HTTP = {
        states.PENDING: 202,
        states.STARTED: 202,
        states.RETRY: 202,
        states.FAILURE: 500,
        states.SUCCESS: 201,
        states.REVOKED: 409,
    }
    """Mapping of Celery result states to HTTP codes."""

    def has_result(self, event):
        """Return true if some result are in the event."""
        return '_tasks' in event.response

    @classmethod
    def _deserialize_result(cls, event):
        """Deserialize celery result stored in event."""
        result = result_from_tuple(event.response['_tasks']['result'])
        parent = result_from_tuple(event.response['_tasks']['parent']) \
            if 'parent' in event.response['_tasks'] else None
        result.parent = parent
        return result

    @classmethod
    def _serialize_result(cls, event, result):
        """Run the task and save the task ids."""
        with db.session.begin_nested():
            event.response.update(
                _tasks={
                    'result': result.as_tuple(),
                }
            )
            if result.parent:
                event.response['_tasks']['parent'] = result.parent.as_tuple()
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

    def delete(self, event):
        """TODO."""
        result = self._deserialize_result(event)
        result.revoke()

    def status(self, event):
        """Get the status."""
        # get raw info from the celery receiver
        raw_info = self._raw_info(event)
        # extract global status
        global_status = ComputeGlobalStatus()
        iterate_result(raw_info=raw_info, fun=global_status)
        # extract information
        info = iterate_result(raw_info=raw_info, fun=collect_info)
        # build response
        return (
            CeleryAsyncReceiver.CELERY_STATES_TO_HTTP.get(
                global_status.status),
            json.dumps(info)
        )

    def persist(self, event, result):
        """Persist event and result after execution."""
        with db.session.begin_nested():
            self._serialize_result(event=event, result=result)
            db.session.add(event)
        db.session.commit()
        update_deposit_state(
            deposit_id=event.payload.get('deposit_id'),
            event_id=event.id,
            sse_channel=event.payload.get('sse_channel')
        )


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    def run(self, event):
        """Create object version and send celery task to download.

        Mandatory fields in the payload:
          * uri, location to download the view.
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

        event_id = str(event.id)

        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])

            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event_id)
            db.session.expunge(event)
        db.session.commit()

        task = download_to_object_version.s(
            object_version=str(object_version.version_id),
            event_id=event_id,
            **event.payload)

        obj_version_id = object_version.version_id

        with db.session.begin_nested():
            object_version = as_object_version(obj_version_id)
            event.response.update(
                links={
                    'self': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=str(object_version.bucket_id),
                        key=object_version.key,
                        _external=True, ),
                    'version': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=str(object_version.bucket_id),
                        key=object_version.key,
                        versionId=str(object_version.version_id),
                        _external=True, ),
                    'cancel': url_for(
                        'invenio_webhooks.event_list',
                        receiver_id='downloader',
                        _external=True, )
                },
                key=object_version.key,
                version_id=str(object_version.version_id),
                tags=object_version.get_tags(),
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

        super(Downloader, self).persist(event=event, result=task.apply_async())

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        return {"file_download": result}


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

        event_id = str(event.id)

        with db.session.begin_nested():
            if 'version_id' in event.payload:
                object_version = as_object_version(event.payload['version_id'])
                first_step = video_metadata_extraction.si(
                    uri=object_version.file.uri,
                    object_version=str(object_version.version_id),
                    deposit_id=event.payload['deposit_id'])
            else:
                object_version = ObjectVersion.create(
                    bucket=event.payload['bucket_id'],
                    key=event.payload['key'])
                ObjectVersionTag.create(object_version, 'uri_origin',
                                        event.payload['uri'])
                first_step = group(
                    download_to_object_version.si(
                        object_version=str(object_version.version_id),
                        event_id=event_id,
                        **event.payload),
                    video_metadata_extraction.si(
                        object_version=str(object_version.version_id),
                        event_id=event_id,
                        **event.payload),
                )

            ObjectVersionTag.create(object_version, '_event_id', event_id)

        mypayload = event.payload
        obj_id = str(object_version.version_id)
        obj_key = object_version.key
        obj_tags = object_version.get_tags()
        db.session.expunge(event)
        db.session.commit()

        presets = mypayload.pop('video_presets', None) or current_app.config[
            'CDS_SORENSON_PRESETS'].keys()
        result = chain(
            first_step,
            group(
                video_extract_frames.si(
                    object_version=str(obj_id),
                    event_id=event_id,
                    **mypayload),
                *[video_transcode.si(object_version=obj_id,
                                     event_id=event_id,
                                     preset=preset,
                                     **mypayload)
                  for preset in presets]
            )
        ).apply_async()

        with db.session.begin_nested():
            event.response.update(
                links=dict(),
                key=obj_key,
                version_id=obj_id,
                tags=obj_tags,
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')

        super(AVCWorkflow, self).persist(event, result)

    def _raw_info(self, event):
        """Get info from the event."""
        result = self._deserialize_result(event)
        first_step = []
        if 'version_id' in event.payload:
            first_step = [{"file_video_metadata_extraction": result.parent}]
        else:
            first_step = [
                {"file_download": result.parent.children[0]},
                {"file_video_metadata_extraction": result.parent.children[1]}
            ]
        second_step = [{"file_video_extract_frames": result.children[0]}]
        for res in result.children[1:]:
            second_step.append({"file_transcode": res})
        return (first_step, second_step)
