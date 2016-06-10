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

""" Search access control. """

from elasticsearch_dsl.query import Q
from flask import g
from invenio_records.api import Record
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter


def cern_read_factory(record, *args, **kwargs):
    """Restrict search results based on CERN groups and user e-mail.

     Records should have an '_access' field containing three nested fields,
     namely 'read', 'write' and 'admin', each having zero or more groups/emails
     that are given the enclosing access right.

     JSON example:

      "_access": [
         {
          "read": ["it-dep-cda", "it-dep", "reader@cern.ch"],
          "write": [], # ANYONE can write!!
          "admin": ["orestis.melkon@cern.ch"]
         }
      ]
    """

    def can(self):
        """Cross-check user's CERN groups with the record's '_access' field."""

        user_groups = [str(need.value) for need in sorted(g.identity.provides)]

        rec = Record.get_record(record.id)

        # Records with no `_access` field are public
        if '_access' not in rec:
            return True

        rec_groups = rec['_access']['read']

        # Records with empty lists are public
        if not rec_groups:
            return True

        return not set(user_groups).isdisjoint(set(rec_groups))

    return type('CERNRead', (), {'can': can})()


def cern_filter():
    """Filter list of results."""

    # Get CERN user's provides
    provides = [str(need.value) for need in sorted(g.identity.provides)]

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
