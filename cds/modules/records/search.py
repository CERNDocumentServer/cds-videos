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


from flask import current_app, g, request
from flask_login import current_user
from invenio_access.permissions import Permission, superuser_access
from invenio_records_rest.errors import InvalidQueryRESTError
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter
from invenio_search.engine import dsl

from .utils import get_user_provides


def lowercase_filter(field_name):
    """Create a term lowercase filter.

    :param field_name: Field name.
    :returns: Lowercase terms for given field.
    """

    def inner(values):
        return dsl.Q("terms", **{field_name: [val.lower() for val in values]})

    return inner


def cern_filter():
    """Filter list of results."""
    # Send empty query for admins
    if Permission(superuser_access).allows(g.identity):
        return dsl.Q()

    # Get CERN user's provides
    provides = get_user_provides()

    # Filter for public records
    public = ~dsl.Q("exists", field="_access.read")
    # Filter for restricted records, that the user has access to
    read_restricted = dsl.Q("terms", **{"_access.read": provides})
    write_restricted = dsl.Q("terms", **{"_access.update": provides})
    # Filter records where the user is owner
    owner = dsl.Q("match", **{"_deposit.created_by": getattr(current_user, "id", 0)})

    # OR all the filters
    combined_filter = public | read_restricted | write_restricted | owner

    return dsl.Q("bool", filter=[combined_filter])


class RecordVideosSearch(RecordsSearch):
    """CERN search class."""

    class Meta:
        """Configuration for CERN search."""

        index = "records-videos-video"
        doc_types = None
        fields = (
            "accelerator_experiment.project",
            "accelerator_experiment.study",
            "accelerator_experiment.experiment",
            "accelerator_experiment.accelerator",
            "accelerator_experiment.facility",
            "category",
            "contributors.email",
            "contributors.name",
            "description^5",
            "keywords.name",
            #"publication_date",  # auto-mapped as a date, and not text. Requires mappings change
            "report_number",
            "title.title^10",
            "title.subtitle",
            "type",
        )
        default_filter = DefaultFilter(cern_filter)


class KeywordSearch(RecordsSearch):
    """Keyword search class.

    It retrieves all keywords (including the deleted).
    """

    class Meta:
        """Configuration for CERN search."""

        index = "keywords-keyword-v1.0.0"
        doc_types = None
        fields = ("*",)


class NotDeletedKeywordSearch(RecordsSearch):
    """Keyword search class.

    It retrieves all keywords except for the deleted ones.
    """

    class Meta:
        """Configuration for CERN search."""

        index = "keywords-keyword-v1.0.0"
        doc_types = None
        fields = ("*",)
        default_filter = DefaultFilter(
            dsl.Q("bool", filter=[dsl.Q("match", deleted=False)])
        )


def query_to_objects(query, cls):
    """Get record object as result of elasticsearch query."""
    results = query.scan()
    ids = [res.meta.id for res in results]
    return cls.get_records(ids)


def query_parser_with_fields(search_obj, qstr=None):
    """Custom query parser with fields."""
    if qstr:
        extra_params = {
            "fields": getattr(search_obj.Meta, "fields", []),
        }
        return dsl.Q("query_string", query=qstr, **extra_params)
    return dsl.Q()


def videos_search_factory(_, search_obj, query_parser=None):
    """Custom query parser."""
    from invenio_records_rest.facets import default_facets_factory
    from invenio_records_rest.sorter import default_sorter_factory

    query_string = request.values.get("q")
    query_parser = query_parser_with_fields(search_obj, query_string)

    try:
        search = search_obj.query(query_parser)
    except SyntaxError:
        current_app.logger.debug(
            "Failed parsing query: {0}".format(request.values.get("q", "")),
            exc_info=True,
        )
        raise InvalidQueryRESTError()

    search_index = getattr(search, "_original_index", search._index)[0]
    search, urlkwargs = default_facets_factory(search, search_index)
    search, sortkwargs = default_sorter_factory(search, search_index)
    for key, value in sortkwargs.items():
        urlkwargs.add(key, value)

    urlkwargs.add("q", query_string)
    return search, urlkwargs
