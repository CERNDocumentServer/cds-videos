# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2026 CERN.
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

"""UTC times as naive datetimes, as ``datetime.utcnow()`` gave them."""

from datetime import datetime, timezone

from invenio_db import db
from sqlalchemy import event


def utcnow():
    """Return the current UTC time without tzinfo.

    Same value as the deprecated ``datetime.utcnow()``, for the columns and
    the comparisons that use naive UTC datetimes.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Timestamp:
    """``created`` and ``updated`` columns in naive UTC.

    Same columns as the ``Timestamp`` of SQLAlchemy-Utils, which still calls
    ``datetime.utcnow()``. The one of Invenio-DB uses timezone aware columns.
    """

    created = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=utcnow, nullable=False)


@event.listens_for(Timestamp, "before_update", propagate=True)
def timestamp_before_update(mapper, connection, target):
    """Update ``updated`` when the row is updated."""
    target.updated = utcnow()
