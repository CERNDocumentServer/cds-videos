# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017, 2018 CERN.
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

"""CDS Admin models."""

from datetime import datetime

from invenio_db import db
from sqlalchemy import and_, or_
from sqlalchemy_utils.models import Timestamp


class Announcement(db.Model, Timestamp):
    """Defines a message to show to users."""

    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)

    message = db.Column(db.Text, nullable=False)
    """The message content."""

    path = db.Column(db.String(100), nullable=True)
    """Define in which /path the message will be visible."""

    style = db.Column(db.String(20), nullable=False)
    """Style of the message, for distinguishing warning or info messages."""

    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now())
    """Start date and time, can be immediate or delayed."""

    end_date = db.Column(db.DateTime, nullable=True)
    """End date and time, must be after `start` or forever."""

    active = db.Column(db.Boolean('active'), nullable=False, default=True)
    """Defines if the message is active, only one at the same time."""

    @classmethod
    def get_for(cls, current_path):
        """Return the active message for the given /path or None."""
        now = datetime.now()
        date_match = and_(Announcement.start_date < now,
                          or_(Announcement.end_date.is_(None),
                              now < Announcement.end_date))
        match = and_(Announcement.active, date_match)

        for ann in Announcement.query.filter(match).all():
            if ann.path is None or current_path.startswith(ann.path):
                return ann

        return None

    @staticmethod
    def disable_expired():
        """Disable any old message to keep everything clean."""
        olds = Announcement.query. \
            filter(and_(Announcement.end_date.isnot(None),
                        Announcement.end_date < datetime.now())). \
            all()

        for old in olds:
            old.active = False

        db.session.commit()
