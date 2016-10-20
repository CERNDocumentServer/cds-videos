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


from flask import Blueprint, abort
from flask.views import MethodView
from invenio_db import db
from invenio_oauth2server import require_api_auth, require_oauth_scopes

from invenio_webhooks.models import Event
from invenio_webhooks.views import error_handler, make_response

blueprint = Blueprint('cds_webhooks', __name__)


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

        from flask_security import current_user
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
