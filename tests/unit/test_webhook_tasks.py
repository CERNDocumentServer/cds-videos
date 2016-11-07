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
"""CDS tests for Webhook Celery tasks."""

from __future__ import absolute_import

import threading

import mock
import time

from cds.modules.webhooks.tasks import download_to_object_version, \
    update_record, video_metadata_extraction
from invenio_files_rest.models import ObjectVersion
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record


def test_download_to_object_version(db, bucket):
    """Test download to object version task."""
    with mock.patch('requests.get') as mock_request:
        obj = ObjectVersion.create(bucket=bucket, key='test.pdf')
        mock_request.return_value = type('Response', (object, ),
                                         {'content': b'\x00' * 1024})

        task = download_to_object_version.s(
            url='http://example.com/test.pdf',
            object_version=str(obj.version_id)
        ).apply()

        db.session.add(obj)
        assert str(obj.version_id) == task.result
        assert obj.file.size == 1024


def test_update_record(app, db):
    # Create record
    recid = str(Record.create({}).id)
    db.session.commit()

    class RecordUpdater(threading.Thread):

        def __init__(self, path, value):
            super(RecordUpdater, self).__init__()
            self.path = path
            self.value = value

        def run(self):
            with app.app_context():
                update_record.s(
                    recid,
                    [{
                        'op': 'add',
                        'path': '/{}'.format(self.path),
                        'value': self.value,
                    }]).apply()

    # Run threads
    thread1 = RecordUpdater('test1', 1)
    thread2 = RecordUpdater('test2', 2)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Check that record was patched properly
    record = Record.get_record(recid)
    assert record.dumps() == {'test1': 1, 'test2': 2}


def test_metadata_extraction(app, db, depid, bucket, online_video):
    # Extract metadata
    obj = ObjectVersion.create(bucket=bucket, key='test.pdf')
    video_metadata_extraction.s(
        uri=online_video,
        object_version=str(obj.version_id),
        deposit_id=depid
    ).apply()

    # Check that deposit's metadata got updated
    recid = PersistentIdentifier.get('depid', depid).object_uuid
    record = Record.get_record(recid)
    assert 'extracted_metadata' in record['_deposit']
    assert record['_deposit']['extracted_metadata']

    # Check that ObjectVersionTags were added
    assert obj.get_tags()


def test_task_failure(app):
    sse_channel = 'test_channel'

    class Listener(threading.Thread):
        def run(self):
            from invenio_sse import current_sse
            with app.app_context():
                current_sse._pubsub.subscribe(sse_channel)
                messages = current_sse._pubsub.listen()
                messages.next()
                message = messages.next()['data']
                assert '"state": "FAILURE"' in message
                assert 'ValueError' in message

    # Establish connection
    listener = Listener()
    listener.start()
    time.sleep(1)

    video_metadata_extraction.s(
        uri='invalid_url',
        object_version='invalid_version_id',
        sse_channel=sse_channel
    ).apply(throw=False)

    listener.join()
