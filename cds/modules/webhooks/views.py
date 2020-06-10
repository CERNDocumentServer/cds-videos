# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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

"""Task status manipulation."""

from __future__ import absolute_import

import json

from flask.views import MethodView
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes

from invenio_webhooks.decorators import (
    need_receiver_permission,
    pass_event,
    pass_user_id,
)
from invenio_webhooks.views import blueprint, error_handler

from .receivers import CeleryAsyncReceiver


class TaskResource(MethodView):
    """Task Endpoint."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_event
    @need_receiver_permission('update')
    def put(self, user_id, receiver_id, event, task_id):
        """Handle PUT request: restart a task."""
        flow = CeleryAsyncReceiver.get_flow(event)
        try:
            flow.restart_task(task_id)
            db.session.commit()
        except KeyError:
            return '', 400
        return '', 204

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_event
    @need_receiver_permission('delete')
    def delete(self, user_id, receiver_id, event, task_id):
        """Handle DELETE request: stop and clean a task."""
        # TODO
        return '', 400


class EventFeedbackResource(MethodView):
    """Event informations."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_event
    @need_receiver_permission('read')
    def get(self, user_id, receiver_id, event):
        """Handle GET request: get more informations."""
        code, status = event.receiver.status(event=event)

        return json.dumps(status), 200


task_item = TaskResource.as_view('task_item')
event_feedback_item = EventFeedbackResource.as_view('event_feedback_item')

blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/events/<string:event_id>'
    '/tasks/<string:task_id>',
    view_func=task_item,
)

blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/events/<string:event_id>/feedback',
    view_func=event_feedback_item,
)
