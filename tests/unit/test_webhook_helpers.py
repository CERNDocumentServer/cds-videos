# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Test cds package."""

from __future__ import absolute_import, print_function

import uuid

from cds.modules.webhooks.helpers import update_deposit_status
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from six import iteritems


def test_deposit_update(depid):
    """Test deposit update."""
    # Generate task ID
    tid = str(uuid.uuid4())

    # Update deposit statuses
    update_deposit_status(depid, tid, 'first', 'started', 1, percentage=0)
    update_deposit_status(depid, tid, 'first', 'done', 1, percentage=100)
    update_deposit_status(depid, tid, 'secondA', 'started', 2, tid='123')
    update_deposit_status(depid, tid, 'secondA', 'done', 2, tid='123')
    update_deposit_status(depid, tid, 'secondB', 'started', 2, tid='123')

    # Check that record was patched properly
    recid = PersistentIdentifier.get('depid', depid).object_uuid
    record = Record.get_record(recid)
    assert 'process' in record['_deposit']
    assert record['_deposit']['process']['task_id'] == tid

    def check_process_keys(process_name, **kwargs):
        entry = record['_deposit']['process'][process_name]
        for key, value in iteritems(kwargs):
            assert key in entry
            assert entry[key] == value

    check_process_keys('first', status='done', order=1, percentage=100)
    check_process_keys('secondA', status='done', order=2, tid='123')
    check_process_keys('secondB', status='started', order=2, tid='123')
