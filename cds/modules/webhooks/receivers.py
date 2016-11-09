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

from flask import url_for
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_webhooks.models import Receiver
from sqlalchemy.orm.attributes import flag_modified

from .tasks import download_to_object_version


def _task_info_extractor(res, children=None):
    """."""
    info = {'id': res.id}
    if hasattr(res, 'status'):
        info['status'] = res.status
    if hasattr(res, 'info'):
        info['info'] = res.info
    if children:
        info['next'] = children
    return info


def _expand_as_tuple(res):
    """."""
    if isinstance(res, (list, tuple)):
        return [_expand_as_tuple(r) for r in res]
    elif res.parent:
        return _task_info_extractor(res, _expand_as_tuple(res.parent))
    elif res.children:
        return _task_info_extractor(res, _expand_as_tuple(res.children))
    else:
        return _task_info_extractor(res)


class CeleryAsyncReceiver(Receiver):
    """TODO."""

    def status(self, event):
        """Return a tuple with current processing status code and message."""
        raise NotImplementedError()

    def delete(self, event):
        """TODO."""
        pass


class Downloader(CeleryAsyncReceiver):
    """Receiver that downloads data from a URL."""

    def run(self, event):
        """Create object version and send celery task to download.

        Mandatory fields in the payload:
          * bucket_id
          * uri
          * deposit_id
          * key

        Optional:
          * parent_deposit_id
          * sse_channel
        """
        assert 'bucket_id' in event.payload
        assert 'uri' in event.payload
        assert 'deposit_id' in event.payload
        assert 'key' in event.payload

        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])

            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event.id)

            if 'sse_channel' not in event.payload:
                deposit_id = event.payload.get('parent_deposit_id',
                                               event.payload['deposit_id'])
                event.payload['sse_channel'] = url_for(
                    'invenio_deposit_sse.depid_sse', pid_value=deposit_id)
                flag_modified(event, 'payload')

            task = download_to_object_version.s(
                event.payload['url'],
                str(object_version.version_id),
                event_id=event.id**event.payload).apply_async(task_id=event.id)

            event.response = dict(
                _tasks=task.as_tuple(),
                links=dict(),
                key=object_version.key,
                version_id=object_version.versrion_id,
                tags=object_version.get_tags(), )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')


class AVCWorkflow(CeleryAsyncReceiver):
    """AVC workflow receiver."""

    def run(self, event):
        """."""
        pass
