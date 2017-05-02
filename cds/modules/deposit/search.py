# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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
"""Configuration for deposit search."""

from __future__ import absolute_import, print_function

from elasticsearch_dsl.query import Q
from flask import current_app, g, request
from flask_login import current_user
from invenio_access.permissions import DynamicPermission, superuser_access
from invenio_records_rest.errors import InvalidQueryRESTError
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter

from ..records.utils import get_user_provides
from .facets import deposit_facets_factory


def deposit_search_factory(self, search):
    """Replace default search factory to use custom facet factory."""
    from invenio_records_rest.sorter import default_sorter_factory
    query_string = request.values.get('q', '')
    query_parser = Q('query_string',
                     query=query_string) if query_string else Q()

    try:
        search = search.query(query_parser)
    except SyntaxError:
        current_app.logger.debug(
            "Failed parsing query: {0}".format(request.values.get('q', '')),
            exc_info=True)
        raise InvalidQueryRESTError()

    search_index = search._index[0]
    search, urlkwargs = deposit_facets_factory(search, search_index)
    search, sortkwargs = default_sorter_factory(search, search_index)
    for key, value in sortkwargs.items():
        urlkwargs.add(key, value)

    urlkwargs.add('q', query_string)
    return search, urlkwargs


def cern_filter():
    """Filter list of results."""
    # Send empty query for admins
    if DynamicPermission(superuser_access).allows(g.identity):
        return Q()

    # Get CERN user's provides
    provides = get_user_provides()

    # Filter for restricted records, that the user has access to
    write_restricted = Q('terms', **{'_access.update': provides})
    # Filter records where the user is owner
    owner = Q('match', **
              {'_deposit.created_by': getattr(current_user, 'id', -1)})

    # OR all the filters
    combined_filter = write_restricted | owner

    return Q('bool', filter=[combined_filter])


class DepositVideosSearch(RecordsSearch):
    """Default search class."""

    class Meta:
        """Configuration for deposit search."""

        index = 'deposits-records-videos-project'
        doc_types = None
        fields = ('*', )
        default_filter = DefaultFilter(cern_filter)
