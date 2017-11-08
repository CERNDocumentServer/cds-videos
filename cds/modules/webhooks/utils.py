# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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

"""Webhooks utils."""

from __future__ import absolute_import

from contextlib import contextmanager
from time import time

from flask import current_app

from invenio_accounts.models import User
from invenio_db import db
from invenio_oauth2server.models import Token


@contextmanager
def get_download_file_url(obj):
    """Create a token and return the url.

    :param obj: The ObjectVersion instance.
    """
    # Create the token for the super user
    with db.session.begin_nested():
        user_token_id = User.query.filter_by(
            email=current_app.config.get('CDS_FILE_TOKEN_SUPER_USER', '')
        ).first().id
        token = Token.create_personal(
            'temp-file-download-{0}'.format(int(time())),
            user_token_id,
            is_internal=True,
        )
    db.session.commit()
    # Return the url
    yield current_app.config.get('FILES_REST_OBJECT_API_ENDPOINT', '').format(
        bucket_id=obj.bucket_id,
        key=obj.key,
        access_token=token.access_token
    )
    # Delete the token
    with db.session.begin_nested():
        db.session.delete(token)
    db.session.commit()
