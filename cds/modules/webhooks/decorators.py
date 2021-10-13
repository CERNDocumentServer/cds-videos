from functools import wraps

from flask_restful import abort

from cds.modules.flows.models import Flow as FlowModel
from cds.modules.flows.api import Flow
from cds.modules.webhooks.errors import ReceiverDoesNotExist, InvalidPayload, \
    WebhooksError
from cds.modules.webhooks.proxies import current_flows
from cds.modules.webhooks.receivers import AVCWorkflow
from flask_login import current_user
from flask import request, jsonify, current_app


def pass_user_id(f):
    """Decorator to retrieve user ID."""
    @wraps(f)
    def inner(self, receiver_id=None, *args, **kwargs):
        try:
            # Attention: assumption that oauth is installed
            user_id = request.oauth.access_token.user_id
        except AttributeError:
            user_id = current_user.get_id()

        kwargs.update(receiver_id=receiver_id, user_id=user_id)
        return f(self, *args, **kwargs)
    return inner


def pass_flow(f):
    """Decorator to retrieve flow."""
    @wraps(f)
    def inner(self, receiver_id=None, flow_id=None, *args, **kwargs):
        flow = FlowModel.query.filter_by(
            receiver_id=receiver_id, id=flow_id
        ).first_or_404()
        flow = Flow(model=flow)
        kwargs.update(receiver_id=receiver_id, flow=flow)
        return f(self, *args, **kwargs)
    return inner


def pass_receiver(f):
    """Decorator to retrieve flow controler."""
    @wraps(f)
    def inner(self, receiver_id=None, *args, **kwargs):
        receiver = current_flows.receivers[receiver_id]
        kwargs.update(receiver=receiver)
        return f(self, *args, **kwargs)
    return inner


def need_receiver_permission(action_name):
    """Decorator for actions on receivers.

    :param action_name: name of the action to perform.
    """
    def need_receiver_permission_builder(f):
        @wraps(f)
        def need_receiver_permission_decorator(self, receiver_id=None,
                                               user_id=None, *args, **kwargs):
            # Get receiver for given receiver ID
            try:
                receiver = AVCWorkflow
            except KeyError:
                raise ReceiverDoesNotExist(receiver_id)
            # Get flow (if it exists)
            flow = kwargs.get('flow')

            # Get receiver's permission method for given action
            can_method = getattr(receiver, 'can')
            # Check if user can perform requested action
            if not can_method(user_id, flow=flow, action=action_name):
                abort(403)

            # Update keyword arguments
            kwargs.update(receiver_id=receiver_id, user_id=user_id)
            if flow is not None:
                kwargs.update(flow=flow)
            return f(self, *args, **kwargs)
        return need_receiver_permission_decorator
    return need_receiver_permission_builder


def error_handler(f):
    """Return a json payload and appropriate status code on exception."""
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
