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
"""Facets for deposit search."""

from flask import current_app
from flask_login import current_user
from invenio_records_rest.facets import _query_filter, _create_filter_dsl
from werkzeug.datastructures import MultiDict


def created_by_me_aggs():
    """Include only my deposits in the aggregation."""
    return {
        'terms': {
            'field': '_deposit.created_by',
            'include': [getattr(current_user, 'id', -1)]
        }
    }


def _aggregations(search, definitions):
    """Add aggregations to query.

    Same as in ``invenio-records-rest`` but allows callables.
    """
    if definitions:
        for name, agg in definitions.items():
            aggreg = agg if not callable(agg) else agg()
            search.aggs[name] = aggreg
    return search


def _post_filter(search, urlkwargs, definitions):
    """Ingest post filter in query."""
    filters, urlkwargs = _create_filter_dsl(urlkwargs, definitions)

    for filter_ in filters:
        search = search.filter(filter_)

    return (search, urlkwargs)


def deposit_facets_factory(search, index):
    """Replace default search factory to use custom facet generator."""
    urlkwargs = MultiDict()

    facets = current_app.config['RECORDS_REST_FACETS'].get(index)

    if facets is not None:
        # Aggregations.
        search = _aggregations(search, facets.get("aggs", {}))

        # Query filter
        search, urlkwargs = _query_filter(search, urlkwargs,
                                          facets.get("filters", {}))

        # Post filter
        search, urlkwargs = _post_filter(search, urlkwargs,
                                         facets.get("post_filters", {}))

    return (search, urlkwargs)
