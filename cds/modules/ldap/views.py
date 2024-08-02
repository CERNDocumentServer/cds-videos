# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
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

"""CDS LDAP views."""

from __future__ import absolute_import, print_function

import ldap
from flask import Blueprint, abort, jsonify, make_response, request

from cds.modules.ldap.client import LdapClient
from cds.modules.ldap.decorators import needs_authentication
from cds.modules.ldap.serializers import serialize_ldap_users

blueprint = Blueprint(
    'cds_ldap',
    __name__,
    url_prefix='/ldap/',
)


@blueprint.route('cern-users/', methods=["GET"])
@needs_authentication
def get_users():
    query = request.args.get('query', '')
    if query:
        try:
            ldap_client = LdapClient()
            results = ldap_client.search_users_by_name(query)
            return make_response(jsonify(serialize_ldap_users(results)), 200)
        except ldap.FILTER_ERROR:
            # fallback to empty results when a special character e.g `\`
            # is passed in the query and ldap throws a `FILTER_ERROR`
            return make_response(jsonify([]), 200)
    abort(400)


@blueprint.route('cern-egroups/', methods=["GET"])
@needs_authentication
def get_egroups():
    query = request.args.get('query', '')
    if query:
        try:
            ldap_client = LdapClient()
            results = ldap_client.search_egroup_by_email(query)
            results += ldap_client.search_user_by_email(query)
            return make_response(jsonify(serialize_ldap_users(results)), 200)
        except ldap.FILTER_ERROR:
            # fallback to empty results when a special character e.g `\`
            # is passed in the query and ldap throws a `FILTER_ERROR`
            return make_response(jsonify([]), 200)
    abort(400)
