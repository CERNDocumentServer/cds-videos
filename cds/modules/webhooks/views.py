# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2021 CERN.
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
from flask_babelex import lazy_gettext as _
from flask import url_for, jsonify, abort, Blueprint, request
from flask.views import MethodView
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_oauth2server.models import Scope

from .decorators import pass_flow, pass_user_id, need_receiver_permission, \
    error_handler, pass_receiver

from .receivers import AVCWorkflow

blueprint = Blueprint('cds_webhooks', __name__)

#
# Required scope
#
webhooks_event = Scope(
    'webhooks:event',
    group='Notifications',
    help_text=_('Allow notifications from external service.'),
    internal=True,
)


def add_link_header(response, links):
    """Add a Link HTTP header to a REST response.

    :param response: REST response instance.
    :param links: Dictionary of links.
    """
    if links is not None:
        response.headers.extend({
            'Link': ', '.join([
                '<{0}>; rel="{1}"'.format(l, r) for r, l in links.items()])
        })


def make_response(flow, receiver):
    """Make a response from flow object."""
    code, message = receiver.serialize_result(flow)
    response = jsonify(message)
    flow.response = message
    db.session.commit()
    response.headers['X-Hub-Delivery'] = flow.id
    add_link_header(response, {'self': url_for(
        '.flow_item', receiver_id=receiver.receiver_id, flow_id=flow.id,
        _external=True
    )})
    return response, code


class TaskResource(MethodView):
    """Task Endpoint."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @need_receiver_permission('update')
    def put(self, user_id, receiver_id, flow, task_id):
        """Handle PUT request: restart a task."""
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
    @pass_flow
    @pass_receiver
    @need_receiver_permission('delete')
    def delete(self, user_id, receiver, receiver_id, event, task_id):
        """Handle DELETE request: stop and clean a task."""
        # TODO not used?
        return '', 400


class FlowFeedbackResource(MethodView):
    """Flow information."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @pass_receiver
    @need_receiver_permission('read')
    def get(self, user_id, receiver, receiver_id, flow):
        """Handle GET request: get more flow information."""
        code, status = receiver.serialize_result(flow)
        return json.dumps(status), 200


class FlowListResource(MethodView):
    """Receiver event hook."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_receiver
    @need_receiver_permission('create')
    def post(self, receiver_id, receiver, user_id):
        """Handle POST request."""
        data = receiver.extract_payload()
        assert data["deposit_id"]
        assert data["version_id"]
        assert data["key"]
        assert data["bucket_id"]
        new_flow = receiver.run(deposit_id=data["deposit_id"],
                                user_id=user_id,
                                version_id=data["version_id"],
                                key=data["key"],
                                bucket_id=data["bucket_id"]
                                )
        db.session.commit()
        return make_response(new_flow, receiver)

    def options(self, receiver_id, receiver):
        """Handle OPTIONS request."""
        abort(405)


class FlowResource(MethodView):
    """Event resource."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @pass_receiver
    @need_receiver_permission('read')
    def get(self, receiver_id, receiver, user_id, flow):
        """Handle GET request - get flow status."""
        return make_response(flow, receiver)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @pass_receiver
    @need_receiver_permission('update')
    def put(self, receiver_id, receiver, user_id, flow):
        """Handle PUT request - restart flow."""
        flow.start()
        db.session.commit()
        return make_response(flow, receiver)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @pass_receiver
    @need_receiver_permission('delete')
    def delete(self, receiver_id, receiver, user_id, flow):
        """Handle DELETE request."""
        flow.delete()
        db.session.commit()
        return make_response(flow, receiver)


task_item = TaskResource.as_view('task_item')
flow_feedback_item = FlowFeedbackResource.as_view('flow_feedback_item')

flow_list = FlowListResource.as_view('flow_list')
flow_item = FlowResource.as_view('flow_item')

blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/flows/',
    view_func=flow_list,
)
blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/flows/<string:flow_id>',
    view_func=flow_item,
)

blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/flows/<string:flow_id>'
    '/tasks/<string:task_id>',
    view_func=task_item,
)

blueprint.add_url_rule(
    '/hooks/receivers/<string:receiver_id>/flows/<string:flow_id>/feedback',
    view_func=flow_feedback_item,
)
