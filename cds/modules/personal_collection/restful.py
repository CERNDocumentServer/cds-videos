# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Rest API for personal collections."""


from collections import MutableSequence
from functools import wraps


from flask import jsonify, request
from flask_login import current_user
from flask_restful import abort, Resource


from invenio.ext.restful import require_header


from .api import (
    create_boxes_content,
    delete_box,
    get_available_box_types,
    set_boxes_settings,
    update_box_content
)
from .errors import PersonalCollectionError


def error_handler(f):
    """Resource error handler."""
    @wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PersonalCollectionError as e:
            if len(e.args) >= 1:
                abort(400, message=e.args[0], status=400)
            else:
                abort(500, message="Ups, this is embarrassing", status=500)
    return inner


class PersonalCollectionResource(Resource):

    """The personal collection resource."""

    method_decorators = [error_handler, ]

    @require_header('Content-Type', 'application/json')
    def get(self, collection):
        """Return for the current user the content of the boxes."""
        return jsonify(dict(
            data=create_boxes_content(current_user.get_id(), collection)
        ))

    @require_header('Content-Type', 'application/json')
    def post(self, collection):
        """Modify the box settings.

        Request parameters:
            - data: new settings, could be `dict` (one box settings) or `list`
              (all boxes settings).
            - index: box index if any

        If the new settings is an instance of a `list`, all the settings for
        the given collection will get updated, if it is instance of `dict`
        only the settings of the given index will be updated.

        The return value depend on the present of the index, if an index is
        given, only the content of this box will be returned, if not, all the
        content.
        """
        if not current_user.is_authenticated():
            abort(401)

        settings = request.get_json().get('data', None)
        index = request.get_json().get('index', None)

        if settings is None:
            raise PersonalCollectionError(
                message='Settings is needed to update the personal collection',
                status=412
            )

        if isinstance(settings, MutableSequence):
            new_settings = set_boxes_settings(
                current_user.get_id(), settings, collection)
            if new_settings is None:
                raise PersonalCollectionError(
                    message="Ups, this is embarrassing.",
                    status=500
                )

        else:
            raise PersonalCollectionError(
                message='A list of dicts is needed', status=412)

        if index is None:
            return jsonify(dict(
                data=create_boxes_content(current_user.get_id(), collection)
            ))
        else:
            return jsonify(dict(
                data=update_box_content(
                    current_user.get_id(), index, collection)
            ))

    @require_header('Content-Type', 'application/json')
    def delete(self, collection):
        """Delete one box from the list of boxes and return the new content."""
        if not current_user.is_authenticated():
            abort(401)

        index = request.get_json().get('index', None)
        if index is None:
            raise PersonalCollectionError(
                message='An index is needed to delete a box.', status=412)

        new_settings = delete_box(current_user.get_id(), index, collection)
        if new_settings is None:
            raise PersonalCollectionError(
                message="Ups, this is embarrassing.",
                status=500
            )
        return jsonify(dict(
            data=create_boxes_content(current_user.get_id(), collection)
        ))


class PersonalCollectionSettingsResource(Resource):

    """The personal collection settings resource."""

    @require_header('Content-Type', 'application/json')
    def get(self):
        """Show the list of available box types."""
        return jsonify(dict(data=get_available_box_types()))


def setup_app(app, api):
    """Setup the resources urls."""
    api.add_resource(
        PersonalCollectionResource,
        '/api/personal_collection/<string:collection>')
    api.add_resource(
        PersonalCollectionSettingsResource,
        '/api/personal_collection/settings')
