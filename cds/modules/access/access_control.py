# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

""" Access control package. """

from elasticsearch_dsl.query import Q
from flask import g
from invenio_records.api import Record
from invenio_records_files.models import RecordsBuckets
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter


#
# Utility functions
#
def _get_user_provides():
    """Extracts the user's provides from g."""
    return [str(need.value) for need in g.identity.provides]


def _has_access(data, action='read'):
    """Check if current user is allowed access to some data."""

    if '_access' not in data:
        return True

    # Get user's provides
    user_groups = _get_user_provides()

    # Get bucket's access rights
    data_groups = data['_access'][action]

    if not data_groups:
        return True

    return not set(user_groups).isdisjoint(set(data_groups))


#
# Records FIXME consider all actions
#
def cern_read_factory(record, *args, **kwargs):
    """Restrict search results based on CERN groups and user e-mail."""

    def can(self):
        """Cross-check user's CERN groups with the record's '_access' field."""

        # Get record
        rec = Record.get_record(record.id)
        # Check access
        return _has_access(rec)

    return type('CERNRead', (), {'can': can})()


#
# Files FIXME consider all actions
#
def cern_file_factory(bucket, action):
    """Restrict file access based on CERN groups and user e-mail."""

    def can(self):
        """Cross-check user's provides with the bucket's '_access' field."""

        # Get record bucket
        rb = RecordsBuckets.query.filter_by(bucket_id=bucket.id).one()
        # Get record
        rec = rb.record.json
        # Check access
        return _has_access(rec)

    return type('CERNFileAccess', (), {'can': can})()


#
# Search
#
def cern_filter():
    """Filter list of results."""

    # Get CERN user's provides
    provides = _get_user_provides()

    # Filter for public records
    public = Q('missing', field='_access.read')
    # Filter for restricted records, that the user has access to
    restricted = Q('terms', **{'_access.read': provides})

    # OR the two filters
    combined_filter = public | restricted

    return Q('bool', filter=[combined_filter])


class CERNRecordsSearch(RecordsSearch):
    """CERN search class."""

    class Meta:
        """Configuration for CERN search."""
        index = '_all'
        doc_types = None
        fields = ('*',)
        default_filter = DefaultFilter(cern_filter)
