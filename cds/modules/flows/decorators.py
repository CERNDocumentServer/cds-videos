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

"""Useful decorators."""
from functools import wraps

from celery import shared_task
from flask import request, jsonify
from flask_login import current_user
from flask_restful import abort

from .api import Flow
from .errors import FlowDoesNotExist, InvalidPayload, FlowsError
from .models import Flow as FlowModel
from .permissions import can
from .task_api import Task


def task(*args, **kwargs):
    """Wrapper around shared task to set default base class."""
    kwargs.setdefault('base', Task)
    return shared_task(*args, **kwargs)


def need_permission(action_name):
    """Decorator for actions on flows.

    :param action_name: name of the action to perform.
    """

    def need_flow_permission_builder(f):
        @wraps(f)
        def need_flow_permission_decorator(self, user_id=None, *args,
                                           **kwargs):
            flow = kwargs.get('flow')

            # Check if user can perform requested action
            if not can(user_id, flow=flow, action=action_name):
                abort(403)

            # Update keyword arguments
            kwargs.update(user_id=user_id)
            if flow is not None:
                kwargs.update(flow=flow)
            return f(self, *args, **kwargs)

        return need_flow_permission_decorator

    return need_flow_permission_builder


def pass_user_id(f):
    """Decorator to retrieve user ID."""
    @wraps(f)
    def inner(self, *args, **kwargs):
        try:
            # Attention: assumption that oauth is installed
            user_id = request.oauth.access_token.user_id
        except AttributeError:
            user_id = current_user.get_id()

        kwargs.update(user_id=user_id)
        return f(self, *args, **kwargs)
    return inner


def pass_flow(f):
    """Decorator to retrieve flow."""
    @wraps(f)
    def inner(self, flow_id=None, *args, **kwargs):
        flow = Flow.get(flow_id)
        kwargs.update(flow=flow)
        return f(self, *args, **kwargs)
    return inner


def error_handler(f):
    """Return a json payload and appropriate status code on exception."""
    @wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except FlowDoesNotExist:
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
        except FlowsError:
            return jsonify(
                status=500,
                description='Internal server error'
            ), 500
    return inner
