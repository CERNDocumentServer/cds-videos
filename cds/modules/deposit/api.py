# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Deposit API."""

from __future__ import absolute_import, print_function

from contextlib import contextmanager

from invenio_db import db
from invenio_deposit.api import Deposit
from invenio_files_rest.models import Bucket, MultipartObject, Location
from invenio_records_files.models import RecordsBuckets


class CDSDeposit(Deposit):
    """Define API for changing deposit state."""

    def is_published(self):
        """Check if deposit is published."""
        return self['_deposit'].get('pid') is not None

    @classmethod
    def create(cls, data, id_=None):
        """Create a deposit.

        Adds bucket creation immediately on deposit creation.
        """
        bucket = Bucket.create(
            default_location=Location.get_default()
        )
        data['_buckets'] = {'deposit': str(bucket.id)}
        deposit = super(CDSDeposit, cls).create(data, id_=id_)
        RecordsBuckets.create(record=deposit.model, bucket=bucket)
        return deposit

    @contextmanager
    def _process_files(self, record_id, data):
        """Snapshot bucket and add files in record during first publishing."""
        if self.files:
            assert not self.files.bucket.locked
            self.files.bucket.locked = True
            snapshot = self.files.bucket.snapshot(lock=True)
            data['_files'] = self.files.dumps(bucket=snapshot.id)
            data['_buckets']['record'] = str(snapshot.id)
            yield data
            db.session.add(RecordsBuckets(
                record_id=record_id, bucket_id=snapshot.id
            ))
        else:
            yield data

    @property
    def multipart_files(self):
        """Get all multipart files."""
        return MultipartObject.query_by_bucket(self.files.bucket)
