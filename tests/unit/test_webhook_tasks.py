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

import mock

from cds.modules.webhooks.tasks import download_to_object_version
from invenio_files_rest.models import ObjectVersion


def test_donwload_to_object_version(bucket):
    """Test download to object version task."""
    with mock.patch('requests.get') as mock_request:
        obj = ObjectVersion.create(bucket=bucket, key='test.pdf')
        mock_request.return_value = type('Response', (object, ),
                                         {'content': b'\x00' * 1024})

        task = download_to_object_version.s('http://example.com/test.pdf',
                                            obj.version_id).apply_async()

        assert str(obj.version_id) == task.result
        assert obj.file.size == 1024
