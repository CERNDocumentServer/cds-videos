# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Configuration for records search."""

from __future__ import absolute_import, print_function

from elasticsearch_dsl.query import Q
from flask import g
from flask_login import current_user
from invenio_access.permissions import DynamicPermission, superuser_access
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter
from invenio_search.utils import schema_to_index

from .utils import get_user_provides
from .api import Keyword


def lowercase_filter(field_name):
    """Create a term lowercase filter.

    :param field_name: Field name.
    :returns: Lowercase terms for given field.
    """
    def inner(values):
        return Q('terms', **{field_name: [val.lower() for val in values]})
    return inner


def cern_filter():
    """Filter list of results."""
    # Send empty query for admins
    if DynamicPermission(superuser_access).allows(g.identity):
        return Q()

    # Get CERN user's provides
    provides = get_user_provides()

    # Filter for public records
    public = Q('missing', field='_access.read')
    # Filter for restricted records, that the user has access to
    read_restricted = Q('terms', **{'_access.read': provides})
    write_restricted = Q('terms', **{'_access.update': provides})
    # Filter records where the user is owner
    owner = Q('match',
              **{'_deposit.created_by': getattr(current_user, 'id', 0)})

    # OR all the filters
    combined_filter = public | read_restricted | write_restricted | owner

    return Q('bool', filter=[combined_filter])


class RecordVideosSearch(RecordsSearch):
    """CERN search class."""

    class Meta:
        """Configuration for CERN search."""

        index = 'records-videos-video'
        doc_types = None
        fields = ('*',)
        default_filter = DefaultFilter(cern_filter)


class KeywordSearch(RecordsSearch):
    """Keyword search class.

    It retrieves all keywords (including the deleted).
    """

    class Meta:
        """Configuration for CERN search."""

        index = schema_to_index(Keyword._schema)[0]
        doc_types = None
        fields = ('*',)


class NotDeletedKeywordSearch(RecordsSearch):
    """Keyword search class.

    It retrieves all keywords except for the deleted ones.
    """

    class Meta:
        """Configuration for CERN search."""

        index = schema_to_index(Keyword._schema)[0]
        doc_types = None
        fields = ('*',)
        default_filter = DefaultFilter(
            Q('bool', filter=[Q('match', deleted=False)])
        )


def query_to_objects(query, cls):
    """Get record object as result of elasticsearch query."""
    results = query.scan()
    ids = [res.meta.id for res in results]
    return cls.get_records(ids)
