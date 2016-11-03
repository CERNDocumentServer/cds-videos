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
          * bucket_id
          * uri
          * deposit_id
          * key

        Optional:
          * parent_deposit_id
        """
        assert 'bucket_id' in event.payload
        assert 'uri' in event.payload
        assert 'deposit_id' in event.payload
        assert 'key' in event.payload

        with db.session.begin_nested():
            object_version = ObjectVersion.create(
                bucket=event.payload['bucket_id'], key=event.payload['key'])

            if 'sse_channel' not in event.payload:
                deposit_id = envent.payload.get('parent_deposit_id',
                                                event.payload['deposit_id'])
                event.payload['sse_channel'] = url_for(
                    'invenio_deposit_sse.depid_sse', pid_value=deposit_id)
                flag_modified(event, 'payload')

            task = download_to_object_version(
                event.payload['url'],
                object_version,
                event_id=envent.id
                **event.payload).apply_async(task_id=event.id)

            ObjectVersionTag.create(object_version, 'uri_origin',
                                    event.payload['uri'])
            ObjectVersionTag.create(object_version, '_event_id', event.id)

            event.response = dict(
                _tasks=task.as_tuple(),
                links=dict(),
                key=object_version.key,
                version_id=object_version.versrion_id,
                tags=object_version.get_tags(), )
            flag_modified(event, 'response')
            flag_modified(event, 'response_headers')
