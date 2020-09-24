# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2020 CERN.
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

"""Flow and task models."""

import logging
import uuid
from enum import Enum, unique

from invenio_db import db
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

logger = logging.getLogger('invenio-flow')


def as_task(value):
    """Get task object from task id or task object.

    :param value: A :class:`invenio_flow.models.Task` or a Task Id.
    :returns:  A :class:`invenio_flow.models.Task` instance.
    """
    return value if isinstance(value, Task) else Task.get(value)


@unique
class Status(Enum):
    """Constants for possible task status."""

    PENDING = 'PENDING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    CANCELED = 'CANCELED'

    @classmethod
    def compute_status(cls, statuses):
        """Compute the general status from a list."""
        # Make statuses always emun in case they are strings, it doesn't hurt much
        statuses = [Status(s) for s in statuses if s is not None]
        if not statuses:
            return cls.PENDING

        if all(s == cls.SUCCESS for s in statuses):
            return cls.SUCCESS

        for status in (cls.PENDING, cls.FAILURE, cls.CANCELED):
            if any(s == status for s in statuses):
                return status

        return cls.PENDING

    @classmethod
    def status_to_http(cls, status):
        """Convert Flow status into HTTP code"""
        STATES_TO_HTTP = {
            cls.PENDING: 202,
            cls.STARTED: 202,
            cls.FAILURE: 500,
            cls.SUCCESS: 201,
            cls.CANCELED: 409,
        }

        try:
            status = Status(status)
        except ValueError:
            pass

        return STATES_TO_HTTP.get(status, 404)

    def __str__(self):
        """Return its value."""
        return self.value


class Flow(db.Model, Timestamp):
    """Flow database model."""

    __tablename__ = 'flows_flow'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4,)
    """Flow identifier."""

    name = db.Column(
        db.String, nullable=False
    )  # TODO: Most likely I don't need this one
    """Flow name."""

    payload = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql',)
        .with_variant(JSONType(), 'sqlite',)
        .with_variant(JSONType(), 'mysql',),
        default=lambda: dict(),
        nullable=True,
    )
    """Flow payload in JSON format, typically args and kwagrs."""

    previous_id = db.Column(
        UUIDType,
        db.ForeignKey('flows_flow.id', onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
    )
    """Task flow instance."""

    @hybrid_property
    def status(self):
        """Overall flow status computed from tasks statuses."""
        return Status.compute_status([t.status for t in self.tasks])

    def __repr__(self):
        """Flow representation."""
        return '<Workflow {name} {status}: {payload}>'.format(**self.to_dict())

    @classmethod
    def get(cls, id_):
        """Get a flow object from the DB."""
        return cls.query.get(id_)

    def to_dict(self):
        """Flow dictionary representation."""
        return {
            'id': str(self.id),
            'created': self.created.isoformat(),
            'updated': self.updated.isoformat(),
            'name': self.name,
            'payload': self.payload,
            'status': str(self.status),
            'previous': str(self.previous_id),
        }


class Task(db.Model, Timestamp):
    """Task database model."""

    __tablename__ = 'flows_task'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4,)
    """Task identifier."""

    previous = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql',)
        .with_variant(JSONType(), 'sqlite',)
        .with_variant(JSONType(), 'mysql',),
        default=lambda: list(),
        nullable=True,
    )
    """List of tasks that need to run before this one, if any.

    This is mainly used by visuals to create the flow diagram.
    """

    flow_id = db.Column(
        UUIDType,
        db.ForeignKey(Flow.id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    """Task flow instance."""

    flow = db.relationship(Flow, backref='tasks')
    """Relationship to the Flow."""

    name = db.Column(db.String, nullable=False)
    """Task name."""

    payload = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql',)
        .with_variant(JSONType(), 'sqlite',)
        .with_variant(JSONType(), 'mysql',),
        default=lambda: dict(),
        nullable=True,
    )
    """Flow payload in JSON format, typically args and kwagrs."""

    status = db.Column(
        db.Enum(Status), nullable=False, default=Status.PENDING,
    )
    """Status of the task, i.e. pending, success, failure."""

    message = db.Column(db.String, nullable=False, default='')
    """Task status message."""

    @classmethod
    def create(cls, name, flow_id, id_=None, payload=None, previous=None):
        """Create a new Task."""
        try:
            with db.session.begin_nested():
                obj = cls(
                    id=id_ or uuid.uuid4(),
                    flow_id=flow_id,
                    name=name,
                    payload=payload or {},
                    previous=previous or [],
                )
                db.session.add(obj)
            logger.info('Created new Flow %s', obj)
        except SQLAlchemyError:
            logger.exception(
                'Failed to create Flow with %s, %s, %s, %s',
                id_,
                flow_id,
                name,
                payload,
            )
            raise
        return obj

    @classmethod
    def get(cls, id_):
        """Get a task object from the DB."""
        return cls.query.get(id_)

    def to_dict(self):
        """Task dictionary representation."""
        return {
            'id': str(self.id),
            'flow_id': str(self.flow_id),
            'created': self.created.isoformat(),
            'updated': self.updated.isoformat(),
            'name': self.name,
            'payload': self.payload,
            'status': str(self.status),
            'message': self.message,
            'previous': self.previous,
        }
