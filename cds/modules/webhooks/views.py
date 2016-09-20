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

from functools import wraps

from flask import Blueprint, jsonify
from flask.views import MethodView
from flask_babelex import lazy_gettext as _
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_oauth2server.models import Scope

from invenio_webhooks.models import Event, InvalidPayload, \
    ReceiverDoesNotExist, WebhookError

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
                description="Receiver does not exists."
            ), 404
        except InvalidPayload as e:
            return jsonify(
                status=415,
                description="Receiver does not support the"
                            " content-type '%s'." % e.args[0]
            ), 415
        except WebhookError:
            return jsonify(
                status=500,
                description="Internal server error"
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

        from flask_security import current_user
        event = Event.create(
            receiver_id=receiver_id,
            user_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()

        # db.session.begin(subtransactions=True)
        event.process()
        db.session.commit()
        return jsonify(**event.response), event.response_code


#
# Register API resources
#
view = ReceiverEventListResource.as_view('event_list')
blueprint.add_url_rule(
    '/cds-hooks/receivers/<string:receiver_id>/events/',
    view_func=view,
)
