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

"""Mock webhook's view to bypass current authorization problem."""

from __future__ import absolute_import, print_function

import json
from functools import wraps

from flask import Blueprint, abort, current_app, jsonify, request, url_for
from flask.views import MethodView
from flask_babelex import lazy_gettext as _
from flask_security import current_user
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_oauth2server.models import Scope

from invenio_webhooks.errors import InvalidPayload, ReceiverDoesNotExist, \
    WebhooksError
from invenio_webhooks.models import Event

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


def make_response(event):
    """Make a response from webhook event."""
    code, message = event.status
    response = jsonify(**event.response)
    response.headers['X-Hub-Event'] = event.receiver_id
    response.headers['X-Hub-Delivery'] = event.id
    if message:
        response.headers['X-Hub-Info'] = message
    add_link_header(response, {'self': url_for(
        '.event_item', receiver_id=event.receiver_id, event_id=event.id,
        _external=True
    )})
    return response, code


#
# Default decorators
#
def error_handler(f):
    """Decorator to handle exceptions."""
    @wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ReceiverDoesNotExist:
            return jsonify(
                status=404,
                description='Receiver does not exists.'
            ), 404
        except InvalidPayload as e:
            return jsonify(
                status=415,
                description='Receiver does not support the'
                            ' content-type "%s".' % e.args[0]
            ), 415
        except WebhooksError:
            return jsonify(
                status=500,
                description='Internal server error'
            ), 500
    return inner


#
# REST Resources
#
class ReceiverEventListResource(MethodView):
    """Receiver event hook."""

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def post(self, receiver_id=None):
        """Handle POST request."""
        event = Event.create(
            receiver_id=receiver_id,
            user_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()

        # db.session.begin(subtransactions=True)
        event.process()
        db.session.commit()
        return make_response(event)

    def options(self, receiver_id=None):
        """Handle OPTIONS request."""
        abort(405)


class ReceiverEventResource(MethodView):
    """Event resource."""

    @staticmethod
    def _get_event(receiver_id, event_id):
        """Find event and check access rights."""
        event = Event.query.filter_by(
            receiver_id=receiver_id, id=event_id
        ).first_or_404()

        if event.user_id != current_user.id:
            abort(401)

        return event

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def get(self, receiver_id=None, event_id=None):
        """Handle GET request."""
        event = self._get_event(receiver_id, event_id)
        return make_response(event)

    @require_api_auth()
    @require_oauth_scopes('webhooks:event')
    @error_handler
    def delete(self, receiver_id=None, event_id=None):
        """Handle DELETE request."""
        event = self._get_event(receiver_id, event_id)
        event.delete()
        db.session.commit()
        return make_response(event)


#
# Register API resources
#
event_list = ReceiverEventListResource.as_view('event_list')
event_item = ReceiverEventResource.as_view('event_item')

blueprint.add_url_rule(
    '/cds-hooks/receivers/<string:receiver_id>/events/',
    view_func=event_list,
)
blueprint.add_url_rule(
    '/cds-hooks/receivers/<string:receiver_id>/events/<string:event_id>',
    view_func=event_item,
)
