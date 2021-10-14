# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
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
import json

from flask import request, jsonify, url_for, Blueprint
from flask.views import MethodView
from flask_restful import abort
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes

from cds.modules.flows.api import Flow
from cds.modules.flows._compat import delete_cached_json_for
from cds.modules.flows.decorators import error_handler, pass_user_id, \
    pass_flow, need_permission
from cds.modules.flows.errors import InvalidPayload
from cds.modules.flows.loaders import extract_payload
from cds.modules.flows.serializers import make_response, serialize_flow

blueprint = Blueprint('cds_webhooks', __name__)


class TaskResource(MethodView):
    """Task Endpoint."""

    @require_api_auth()
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('update')
    def put(self, user_id, flow, task_id):
        """Handle PUT request: restart a task."""
        try:
            flow.restart_task(task_id)
            db.session.commit()
        except KeyError:
            return '', 400
        return '', 204

    @require_api_auth()
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('delete')
    def delete(self, user_id, flow, task_id):
        """Handle DELETE request: stop and clean a task."""
        # TODO not used?
        return '', 400


class FlowFeedbackResource(MethodView):
    """Flow information."""

    @require_api_auth()
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('read')
    def get(self, user_id, flow):
        """Handle GET request: get more flow information."""
        code, status = serialize_flow(flow)
        return json.dumps(status), code


class FlowListResource(MethodView):
    """List view of Flow resource."""

    @require_api_auth()
    @error_handler
    @pass_user_id
    @need_permission('create')
    def post(self, user_id):
        """Handle POST request."""
        data = extract_payload()
        assert data["deposit_id"]
        assert data.get("version_id") or data.get("uri")
        assert data["key"]
        new_flow = Flow(deposit_id=data["deposit_id"],
                        user_id=user_id,
                        payload=dict(
                            version_id=data.get("version_id"),
                            key=data["key"],
                            bucket_id=data.get("bucket_id"),
                            uri=data.get("uri"),
                            deposit_id=data.get("deposit_id")
                        )
                        )
        new_flow.run()
        db.session.commit()
        return make_response(new_flow)

    def options(self, receiver_id, receiver):
        """Handle OPTIONS request."""
        abort(405)


class FlowResource(MethodView):
    """Flow resource."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('read')
    def get(self, user_id, flow):
        """Handle GET request - get flow status."""
        return make_response(flow)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('update')
    def put(self, user_id, flow):
        """Handle PUT request - restart flow."""
        flow.start()
        db.session.commit()
        return make_response(flow)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    @pass_user_id
    @pass_flow
    @need_permission('delete')
    def delete(self, user_id, flow):
        """Handle DELETE request."""
        flow.delete()
        db.session.commit()
        return make_response(flow)


task_item = TaskResource.as_view('task_item')
flow_feedback_item = FlowFeedbackResource.as_view('flow_feedback_item')

flow_list = FlowListResource.as_view('flow_list')
flow_item = FlowResource.as_view('flow_item')

blueprint.add_url_rule(
    '/flows/',
    view_func=flow_list,
)
blueprint.add_url_rule(
    '/flows/<string:flow_id>',
    view_func=flow_item,
)

blueprint.add_url_rule(
    '/flows/<string:flow_id>/tasks/<string:task_id>',
    view_func=task_item,
)

blueprint.add_url_rule(
    '/flows/<string:flow_id>/feedback',
    view_func=flow_feedback_item,
)
