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
from invenio_db import db
from celery import states
from flask import url_for
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified
from celery.result import result_from_tuple
import json
import os

from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_object_version)

from .tasks import (download_to_object_version, video_extract_frames,
                    video_metadata_extraction, video_transcode)


def _compute_status(statuses):
    for status_to_check in [states.FAILURE, states.STARTED, states.RETRY,
                            states.PENDING]:
        if any(status == status_to_check for status in statuses):
            return status_to_check
    return states.SUCCESS


def _info_extractor(res, name, children=None):
    """Return all tasks information."""
    info = {'id': res.id}
    if hasattr(res, 'status'):
        info['status'] = res.status
    if hasattr(res, 'info'):
        info['info'] = str(res.info)
    if children:
        info['next'] = children
    if hasattr(res, 'result'):
        info['result'] = str(res.result)
    info['name'] = name
    return info


class CeleryAsyncReceiver(Receiver):
    """TODO."""

    CELERY_STATES_TO_HTTP = {
        states.PENDING: 202,
        states.STARTED: 202,
        states.RETRY: 202,
        states.FAILURE: 500,
        states.SUCCESS: 201,
        states.REVOKED: 409,
    }
    """Mapping of Celery result states to HTTP codes."""

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
        """Revoke all associated tasks."""
        result = self._deserialize_result(event)
        result.revoke(terminate=True)

    @staticmethod
    def _make_status_response(status, info):
        """Make a response."""
        return (
            CeleryAsyncReceiver.CELERY_STATES_TO_HTTP.get(status),
            json.dumps(info)
        )

    def status(self, event):
        """Get the status."""
        return self._make_status_response(**self._status_and_info(
            event=event))


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    generated_objects = {}
    """Stores generated resources that require de-allocation."""

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
        bucket_id = event.payload['bucket_id']
        key = event.payload['key']

        with db.session.begin_nested():
            object_version = ObjectVersion.create(bucket=bucket_id, key=key)
            obj_id = str(object_version.version_id)
            self.generated_objects[event_id] = obj_id
            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event_id)
            db.session.expunge(event)
        db.session.commit()

        task = download_to_object_version.s(
            object_version=obj_id,
            event_id=event_id,
            **event.payload)

        self._serialize_result(event=event, result=task.apply_async())

        with db.session.begin_nested():
            object_version = as_object_version(obj_id)
            event.response.update(
                links={
                    'self': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=bucket_id, key=key, _external=True,
                    ),
                    'version': url_for(
                        'invenio_files_rest.object_api',
                        bucket_id=bucket_id, key=key,
                        version_id=obj_id, _external=True,
                    ),
                    'cancel': url_for(
                        'invenio_webhooks.event_item',
                        receiver_id='downloader',
                        event_id=event_id,
                        _external=True,
                    ),
                },
                key=key,
                version_id=obj_id,
                tags=object_version.get_tags(),
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
            db.session.add(event)
        db.session.commit()

    def _status_and_info(self, event, fun=_info_extractor):
        """Get status and info from the event."""
        result = self._deserialize_result(event)
        status = result.status
        info = fun(result, 'file_download')
        return {'status': status, 'info': info}

    def delete(self, event):
        """Delete generated files."""
        super(Downloader, self).delete(event)
        dispose_object_version(self.generated_objects[str(event.id)])


class AVCWorkflow(CeleryAsyncReceiver):
    """AVC workflow receiver."""

    generated_objects = {}
    """Stores generated resources that require de-allocation."""

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
                obj_id = event.payload['version_id']
                object_version = as_object_version(obj_id)
                first_step = video_metadata_extraction.si(
                    uri=object_version.file.uri,
                    object_version=obj_id,
                    deposit_id=event.payload['deposit_id'])
            else:
                object_version = ObjectVersion.create(
                    bucket=event.payload['bucket_id'],
                    key=event.payload['key'])
                obj_id = str(object_version.version_id)
                self.generated_objects[event_id] = obj_id
                ObjectVersionTag.create(object_version, 'uri_origin',
                                        event.payload['uri'])
                first_step = group(
                    download_to_object_version.si(
                        object_version=obj_id,
                        event_id=event_id,
                        **event.payload),
                    video_metadata_extraction.si(
                        object_version=obj_id,
                        event_id=event_id,
                        **event.payload),
                )

            ObjectVersionTag.create(object_version, '_event_id', event_id)

        mypayload = event.payload
        obj_key = object_version.key
        obj_tags = object_version.get_tags()
        db.session.expunge(event)
        db.session.commit()

        result = chain(
            first_step,
            group(
                video_transcode.si(object_version=obj_id,
                                   event_id=event_id,
                                   **mypayload),
                video_extract_frames.si(object_version=obj_id,
                                        event_id=event_id,
                                        **mypayload), ),
        ).apply_async()

        with db.session.begin_nested():
            self._serialize_result(event=event, result=result)

            event.response.update(
                links={
                    'cancel': url_for(
                        'invenio_webhooks.event_item',
                        receiver_id='avc',
                        event_id=event_id,
                        _external=True,
                    ),
                },
                key=obj_key,
                version_id=obj_id,
                tags=obj_tags,
            )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
            db.session.add(event)
        db.session.commit()

    def _status_and_info(self, event, fun=_info_extractor):
        """Get status and info from the event."""
        result = self._deserialize_result(event)
        if 'version_id' in event.payload:
            status = _compute_status([
                result.parent.status,
                result.children[0].status,
                result.children[1].status
            ])
            info = fun(result.parent, 'file_video_metadata_extraction', [
                fun(result.children[0], 'file_transcode'),
                fun(result.children[1], 'file_video_extract_frames')
            ])
        else:
            status = _compute_status([
                result.parent.children[0].status,
                result.parent.children[1].status,
                result.children[0].status,
                result.children[1].status,
            ])
            info = [
                [
                    fun(result.parent.children[0], 'file_download'),
                    fun(result.parent.children[1],
                        'file_video_metadata_extraction'),
                ],
                [
                    fun(result.children[0], 'file_transcode'),
                    fun(result.children[1], 'file_video_extract_frames'),
                ]
            ]
        return {'status': status, 'info': info}

    def delete(self, event):
        """Delete generated files."""
        super(AVCWorkflow, self).delete(event)
        dispose_master_object(self.generated_objects[str(event.id)])


#
# Resource cleaning
#
def dispose_master_object(master_id):
    """Delete all resources related to an ObjectVersion."""
    # Delete all slave objects
    for slave_id in [slave.version_id
                     for slave in ObjectVersion.query.all()
                     if slave.get_tags().get('master') == master_id]:
        dispose_object_version(slave_id)

    # Delete master object
    dispose_object_version(master_id)


def dispose_object_version(object_version_id):
    """Delete an ObjectVersion, as well as its FileInstance and actual file."""
    with db.session.begin_nested():
        if object_version_id:
            master = as_object_version(object_version_id)
            master_file = master.file
            if master_file:
                master_uri = master_file.uri
                master.remove()  # delete ObjectVersion
                master_file.delete()  # delete FileInstance
                os.remove(master_uri)  # delete actual file
            else:
                master.remove()
    db.session.commit()  # commit changes
