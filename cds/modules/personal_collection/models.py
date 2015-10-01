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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Personal collection database model."""

import six
import sys

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.mutable import MutableDict


from invenio_ext.sqlalchemy import db
from invenio_accounts.models import User


from .config import DEFAULT_SETTINGS


class PersonalCollectionSettings(db.Model):

    """Represents the user setting for her/his personal collections.

    The `settings` column contains a dictionary with the configurations for
    each collection:

        {
            'home': [
                {'type': 'record_list',
                 'title':"Ellis' articles",
                 'query': 'author:John Ellis'
                },
                {'type': 'loan_list',
                 'title': 'My Loans'
                },
                {'type': 'image',
                 'title': 'Latest photo'
                 'collection': 'Photos',
                 'pick': 'latest'
                }
            ],
            'collection2': {
                .....
            },
            ....
        }
    """

    __tablename__ = 'personal_colletion_settings'

    id = db.Column(
        db.Integer(15, unsigned=True),
        db.ForeignKey(User.id), primary_key=True)
    """ User id."""

    settings = db.Column(MutableDict.as_mutable(db.JSON), nullable=False)

    user = db.relationship("User", backref="uid")

    @classmethod
    def get(cls, user_id, collection='home'):
        """Get settings.

        :param user_id: User ID as in `invenio_accounts.models:User`
        :param collection: Name of the collection to get the settings from, by
            default it fetches for the `home` collection
        :returns: Returns empty `dict` if not settings were found.

        """
        if user_id is None or user_id in [-1, 0]:
            return DEFAULT_SETTINGS.get(collection, {})

        obj = cls.query.get(user_id)
        if obj:
            return obj.settings.get(
                collection, DEFAULT_SETTINGS.get(collection, {}))
        else:
            try:
                obj = cls(id=user_id, settings=DEFAULT_SETTINGS)
                db.session.add(obj)
                db.session.commit()
                return obj.settings.get(collection, {})
            except SQLAlchemyError:
                current_app.logger.exception(
                    "Failed to save changes to collection settings")
                db.session.rollback()
                six.reraise(*sys.exc_info())

    @classmethod
    def set(cls, user_id, settings, collection='home'):
        """Set settings for a concrete collection.

        If the settings for the given `user_id` does not exist, sets the
        default ones and the updates them with the given `settings`.

        :param user_id: User ID as in `invenio_accounts.models:User`
        :param settings: `dict` with the collection settings
        :param collection: Collection name, home collection by default
        :returns: TODO

        """
        obj = cls.query.get(user_id)
        try:
            if obj is None:
                obj = cls(id=user_id, settings=DEFAULT_SETTINGS)
            obj.settings[collection] = settings
            obj.settings.changed()
            db.session.commit()
            return obj.settings[collection]
        except SQLAlchemyError:
            current_app.logger.exception(
                "Failed to save changes to collection settings")
            db.session.rollback()
            six.reraise(*sys.exc_info())
