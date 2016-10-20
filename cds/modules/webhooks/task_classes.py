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

"""Celery task classes for Webhook Receivers."""

from __future__ import absolute_import, division

from cds.modules.webhooks.helpers import update_deposit_status
from celery import Task
from celery.result import AsyncResult
from celery.states import STARTED, FAILURE, state as state_cls
from invenio_db import db
from sqlalchemy.exc import SQLAlchemyError


class Orchestrator(Task):
    """Task base for orchestrating task workflows."""

    abstract = True

    def set_state(self, task_name, task_meta):
        """Update orchestrator's state with sub-task's meta information."""
        raise NotImplementedError()


class AVCOrchestrator(Orchestrator):
    """Orchestrator for the AVC workflow."""

    abstract = True

    def clear_state(self):
        """Initialize orchestrator's state."""
        self.update_state(state=STARTED, meta={})

    def set_state(self, task_name, task_meta):
        """Accumulate all subtasks' states inside orchestrator's state."""

        # Get current task progresses
        result = AsyncResult(self.request.id)
        progresses = result.info or {}

        # Set status for current sub-task
        progresses.update({task_name: task_meta})

        # Update state
        self.update_state(state=STARTED, meta=progresses)

    def update_deposit(self, name, status, order, **kwargs):
        """Update deposit status."""
        update_deposit_status(self.dep_id, self.request.id, name,
                              status, order, **kwargs)


class ProgressTask(Task):
    """Base class for tasks that report their progress inside their state."""

    abstract = True

    @property
    def task_name(self):
        """Extract only the task name from the task's canonical name."""
        return self.name.split('.')[-1]

    def __call__(self, *args, **kwargs):
        """Set workflow-specific parameters automatically from given kwargs."""

        # Begin DB session
        if self.db_session:
            db.session.begin(nested=True)

        # Set task's parent
        if 'parent' in kwargs:
            self.parent = kwargs['parent']
            del kwargs['parent']
        else:
            self.parent = None

        # Set deposit status to 'STARTED'
        self.update_deposit('STARTED')

        return_value = self.run(*args, **kwargs)

        # Set deposit status to 'DONE'
        self.update_deposit('DONE')

        # Commit session
        if self.db_session:
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                raise

        return return_value

    def set_state(self, state, meta):
        """Update tasks's state."""

        # Update internal (atomic) state
        self.update_state(
            state=state if isinstance(state, state_cls) else state_cls(state),
            meta=meta,
        )

        # Notify parent with status change
        if self.parent:
            self.parent.set_state(self.task_name, meta)

    def update_progress(self, percentage):
        """Report progress of a Celery task."""
        self.set_state(STARTED, dict(
            percentage=percentage,
            order=self.order,
        ))

    def update_progress_with_size(self, size, total):
        """Report progress of downloading celery task."""
        self.update_progress(size / total * 100)

    def update_deposit(self, status):
        """Update parent's deposit status."""
        if self.parent:
            self.parent.update_deposit(self.task_name, status, self.order)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Gracefully handle task exceptions."""
        self.set_state(FAILURE, dict(message=str(einfo.exception)))


def with_order(order=0, db_session=False):
    """Factory method for creating ProgressTasks with fixed order."""
    return type(
        # Name
        'ExtendedTask',
        # Bases
        (ProgressTask, ),
        # Attributes
        {
            'abstract': True,
            'order': order,
            'db_session': db_session,
        }
    )
