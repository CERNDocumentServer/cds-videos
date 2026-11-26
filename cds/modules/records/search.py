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

import re

from flask import current_app, g, request
from flask_login import current_user
from invenio_access.permissions import Permission, superuser_access
from invenio_records_rest.errors import InvalidQueryRESTError
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter
from invenio_search.engine import dsl

from .utils import get_user_provides

# System / facet fields used as Lucene filters but not always in Meta.fields.
_EXTRA_FILTER_FIELDS = frozenset(
    {
        "featured",
        "vr",
        "_deposit.id",
        "_deposit.created_by",
        "category",
        "type",
        "language",
    }
)


def _filter_field_names(search_obj):
    """Field names that may appear as ``field:value`` in a query."""
    names = set(_EXTRA_FILTER_FIELDS)
    for field in getattr(search_obj.Meta, "fields", ()):
        names.add(field.split("^", 1)[0])
    return names


def _looks_like_field_filter(qstr, search_obj):
    """True only for known ``field:…`` filters, not title text with a colon.

    Allows optional spaces after the colon (``title.title: "Higgs"``) and a
    leading ``(``. Unknown prefixes like ``Prize:Steven`` stay on the free-text
    path.
    """
    if not qstr:
        return False
    names = sorted(_filter_field_names(search_obj), key=len, reverse=True)
    pattern = r"(?:^|\s|\()(?:{0})\s*:".format(
        "|".join(re.escape(name) for name in names)
    )
    return re.search(pattern, qstr) is not None


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
            "doi^8",
            "keywords.name",
            "language",
            "legacy_recid",
            "publication_date",
            "report_number^8",
            "title.title^10",
            "title.subtitle",
            "translations.description^3",
            "translations.title.title^5",
            "translations.title.subtitle",
            "type",
        )
        # Extra phrase boosts for exact-ish ranking (#1822)
        phrase_fields = (
            ("title.title", 25),
            ("description", 10),
            ("translations.title.title", 15),
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


def title_suggest_search(qstr, size=10):
    """Title typeahead via filtered search (same access as ``/api/records/``).

    Completion suggesters ignore query filters, so we use ``RecordVideosSearch``
    (``cern_filter``) with a prefix query on ``title.title`` instead.
    """
    size = size or 10
    search = (
        RecordVideosSearch()
        .source(["title"])
        .params(size=size)
        .query("match_phrase_prefix", **{"title.title": qstr})
    )
    options = []
    for hit in search.execute():
        title = (hit.to_dict().get("title") or {}).get("title")
        if not title:
            continue
        options.append({"text": title, "_source": {"title": {"title": title}}})
    return options


def query_parser_with_fields(search_obj, qstr=None):
    """Custom query parser with boosted fields.

    Uses ``simple_query_string`` so pasted titles with quotes/colons do not
    raise OpenSearch syntax errors (unlike ``query_string``).

    Do **not** search ``*``: long pastes × all mapped fields exceed
    ``indices.query.bool.max_clause_count`` (1024). Prefer an explicit boosted
    field list instead (ILS-style catch-all is unsafe at paste length).

    Adds optional ``match_phrase`` should-clauses (``Meta.phrase_fields``) so
    exact phrases in titles/descriptions rank above loose word matches.
    """
    if not qstr:
        return dsl.Q()
    fields = list(getattr(search_obj.Meta, "fields", ()))
    # Known field filters still need query_string. Free text uses
    # simple_query_string so quotes/colons in titles do not 500.
    if _looks_like_field_filter(qstr, search_obj):
        base = dsl.Q(
            "query_string",
            query=qstr,
            fields=fields,
            lenient=True,
        )
    else:
        # Disable NOT: bare ``-`` in report numbers (CERN-VIDEO-1997-001)
        # would otherwise mean exclusion and match the wrong set of docs.
        base = dsl.Q(
            "simple_query_string",
            query=qstr,
            fields=fields,
            lenient=True,
            # AND so hyphenated report numbers (hyphens stripped by analyzer)
            # do not become a giant OR of CERN|VIDEO|1997|001 matching everything.
            # Disable NOT so bare ``-`` is not an exclusion operator.
            default_operator="and",
            flags="AND|OR|PREFIX|PHRASE|PRECEDENCE|ESCAPE|WHITESPACE|FUZZY|NEAR|SLOP",
        )
    should = []
    for field, boost in getattr(search_obj.Meta, "phrase_fields", ()):
        should.append(
            dsl.Q("match_phrase", **{field: {"query": qstr, "boost": boost}})
        )
    for field, boost in getattr(
        search_obj.Meta,
        "exact_fields",
        (("report_number.raw", 30),),
    ):
        should.append(dsl.Q("term", **{field: {"value": qstr, "boost": boost}}))
    if not should:
        return base
    # Prefer exact report_number/DOI hits even when free-text parsing is weak.
    return dsl.Q("bool", should=[base, *should], minimum_should_match=1)


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
