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

from invenio_db import db
from flask.views import MethodView
from invenio_webhooks.views import blueprint, error_handler
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_webhooks.views import ReceiverEventResource

from .receivers import build_task_payload
from .status import iterate_result, collect_info, ResultEncoder


class TaskResource(MethodView):
    """Task Endpoint."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def put(self, receiver_id, event_id, task_id):
        """Handle PUT request: restart a task."""
        event = ReceiverEventResource._get_event(receiver_id, event_id)
        payload = build_task_payload(event, task_id)
        if payload:
            event.receiver.rerun_task(**payload)
            db.session.commit()
            return '', 204
        return '', 400

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def delete(self, receiver_id, event_id, task_id):
        """Handle DELETE request: stop and clean a task."""
        event = ReceiverEventResource._get_event(receiver_id, event_id)
        payload = build_task_payload(event, task_id)
        if payload:
            event.receiver.clean_task(**payload)
            db.session.commit()
            return '', 204
        return '', 400


class EventFeedbackResource(MethodView):
    """Event informations."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def get(self, receiver_id, event_id):
        """Handle GET request: get more informations."""
        event = ReceiverEventResource._get_event(receiver_id, event_id)
        raw_info = event.receiver._raw_info(event=event)

        def collect(task_name, result):
            if isinstance(result.info, Exception):
                (args,) = result.info.args
                return {
                    'id': result.id,
                    'status': result.status,
                    'info': args,
                    'name': task_name
                }
            else:
                return collect_info(task_name, result)

        result = iterate_result(
            raw_info=raw_info, fun=collect)
        return ResultEncoder().encode(result), 200


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
