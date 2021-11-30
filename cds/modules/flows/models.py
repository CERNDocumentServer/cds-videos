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

from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

logger = logging.getLogger("cds-flow")


def as_task(value):
    """Get task object from task id or task object.

    :param value: A :class:`invenio_flow.models.TaskMetadata` or a Task Id.
    :returns:  A :class:`invenio_flow.models.TaskMetadata` instance.
    """
    return (
        value if isinstance(value, FlowTaskMetadata) else FlowTaskMetadata.get(value)
    )


class FlowMetadata(db.Model, Timestamp):
    """Flow database model."""

    __tablename__ = "flows_flow"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Flow identifier."""

    name = db.Column(db.String, nullable=False)
    """Flow name."""

    payload = db.Column(
        db.JSON()
        .with_variant(
            postgresql.JSONB(none_as_null=True),
            "postgresql",
        )
        .with_variant(
            JSONType(),
            "sqlite",
        )
        .with_variant(
            JSONType(),
            "mysql",
        ),
        default=lambda: dict(),
        nullable=True,
    )

    is_last = db.Column(db.Boolean, default=True)
    """Flag pointing to the last flow associated with a deposit."""

    user_id = db.Column(db.Integer(), db.ForeignKey(User.id), nullable=False)
    """User who triggered the flow."""

    deposit_id = db.Column(db.String, nullable=False)
    """Deposit for which the flow was triggered."""

    @hybrid_property
    def status(self):
        """Overall flow status computed from tasks statuses."""
        return FlowTaskStatus.compute_status([t.status for t in self.tasks])

    @classmethod
    def get(cls, id_):
        """Get a flow object from the DB."""
        return cls.query.get(id_)

    @classmethod
    def create(
            cls, deposit_id, name="AVCWorkflow", payload=None, user_id=None
    ):
        """Create a new flow instance and store it in the database."""
        with db.session.begin_nested():
            obj = cls(
                name=name,
                payload=payload or dict(),
                user_id=user_id,
                deposit_id=deposit_id,
            )
            db.session.add(obj)
        return obj

    @classmethod
    def get_by_deposit(cls, deposit_id, is_last=True, multiple=False):
        """Get tasks by deposit id."""
        query = FlowMetadata.query.filter_by(
            deposit_id=str(deposit_id)
        ).filter_by(is_last=is_last)

        return query.all() if multiple else query.one_or_none()

    def to_dict(self):
        """Flow dictionary representation."""
        return {
            "id": str(self.id),
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "name": self.name,
            "payload": self.payload,
            "status": str(self.status),
            "tasks": [t.to_dict() for t in self.tasks],
            "user": str(self.user_id),
        }

    def __repr__(self):
        """Flow representation."""
        return "<Workflow {name} {status}: {payload}>".format(**self.to_dict())


@unique
class FlowTaskStatus(Enum):
    """Constants for possible task status."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"

    @classmethod
    def compute_status(cls, statuses):
        """Compute the general status from a list."""
        # make sure each item is an enum
        statuses = [FlowTaskStatus(s) for s in statuses if s is not None]
        if not statuses or cls.PENDING in statuses:
            return cls.PENDING

        # no PENDING
        if cls.STARTED in statuses:
            return cls.STARTED

        # no PENDING or STARTED
        if cls.FAILURE in statuses:
            return cls.FAILURE

        # no PENDING or STARTED or FAILURE
        if cls.SUCCESS in statuses:
            return cls.SUCCESS

        # it should not happened that all are CANCELLED, but just in case
        return cls.CANCELLED

    @classmethod
    def status_to_http(cls, status):
        """Convert Flow state into HTTP code."""
        STATES_TO_HTTP = {
            cls.PENDING: 201,
            cls.STARTED: 201,
            cls.FAILURE: 500,
            cls.SUCCESS: 200,
            cls.CANCELLED: 409,
        }

        status = FlowTaskStatus(status)
        return STATES_TO_HTTP.get(status, 404)

    def __str__(self):
        """Return its value."""
        return self.value


class FlowTaskMetadata(db.Model, Timestamp):
    """Flow Task database model."""

    __tablename__ = "flows_task"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Task identifier."""

    flow_id = db.Column(
        UUIDType,
        db.ForeignKey(FlowMetadata.id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    """Task flow instance."""

    flow = db.relationship(FlowMetadata, backref="tasks", lazy="subquery")
    """Relationship to the FlowMetadata."""

    name = db.Column(db.String, nullable=False)
    """Task name."""

    payload = db.Column(
        db.JSON()
        .with_variant(
            postgresql.JSONB(none_as_null=True),
            "postgresql",
        )
        .with_variant(
            JSONType(),
            "sqlite",
        )
        .with_variant(
            JSONType(),
            "mysql",
        ),
        default=lambda: dict(),
        nullable=True,
    )
    """Flow payload in JSON format, typically args and kwagrs."""

    status = db.Column(
        db.Enum(FlowTaskStatus),
        nullable=False,
        default=FlowTaskStatus.PENDING,
    )
    """Status of the task, i.e. pending, success, failure."""

    message = db.Column(db.String, nullable=False, default="")
    """Task status message."""

    @classmethod
    def create(cls, flow_id, name, payload=None, status=FlowTaskStatus.PENDING):
        """Create a new Task."""
        try:
            with db.session.begin_nested():
                obj = cls(
                    flow_id=flow_id,
                    name=name,
                    payload=payload or {},
                    status=status,
                )
                db.session.add(obj)
            logger.info("Created new Task %s", obj)
        except SQLAlchemyError:
            logger.exception(
                "Failed to create Task with %s, %s, %s",
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

    @classmethod
    def get_all_by_flow_task_name(cls, flow_id, name):
        """Get tasks by flow id and name."""
        return cls.query.filter_by(flow_id=flow_id, name=name).all()

    def to_dict(self):
        """Task dictionary representation."""
        return {
            "id": str(self.id),
            "flow_id": str(self.flow_id),
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "name": self.name,
            "payload": self.payload,
            "status": str(self.status),
            "message": self.message,
        }
