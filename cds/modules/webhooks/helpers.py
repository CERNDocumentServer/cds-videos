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

"""Helpers for Webhook Receivers."""

from __future__ import absolute_import, division

from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record


def update_deposit_status(dep_id, task_id, task_name, status, order, **kwargs):
    """Update status of a deposit (i.e. patch json metadata)."""

    # Get corresponding record
    recid = PersistentIdentifier.get('depid', dep_id).object_uuid
    record = Record.get_record(recid)

    # Create process key
    if 'process' not in record['_deposit']:
        record = record.patch([{
            'op': 'add',
            'path': '/_deposit/process',
            'value': {'task_id': task_id}
        }])

    # Update task status
    record = record.patch([{
        'op': 'add',
        'path': '/_deposit/process/{}'.format(task_name),
        'value': dict(
            status=status,
            order=order,
            **kwargs
        )
    }])

    # Commit status update
    record.commit()
    db.session.commit()
