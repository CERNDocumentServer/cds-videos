# # -*- coding: utf-8 -*-
# #
# # This file is part of Invenio.
# # Copyright (C) 2016 CERN.
# #
# # Invenio is free software; you can redistribute it
# # and/or modify it under the terms of the GNU General Public License as
# # published by the Free Software Foundation; either version 2 of the
# # License, or (at your option) any later version.
# #
# # Invenio is distributed in the hope that it will be
# # useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# # General Public License for more details.
# #
# # You should have received a copy of the GNU General Public License
# # along with Invenio; if not, write to the
# # Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# # MA 02111-1307, USA.
# #
# # In applying this license, CERN does not
# # waive the privileges and immunities granted to it by virtue of its status
# # as an Intergovernmental Organization or submit itself to any jurisdiction.

# """Default configuration of deposit module."""

from invenio_records_rest.facets import terms_filter

# from invenio_records_rest.utils import check_search

# from .utils import check_oauth2_scope_write, check_oauth2_scope_write_elasticsearch

DEPOSIT_SEARCH_API = "/api/deposits"
# """URL of search endpoint for deposits."""

DEPOSIT_RECORDS_API = "/api/deposits/{pid_value}"
# """URL of record endpoint for deposits."""

DEPOSIT_FILES_API = "/api/files"
# """URL of files endpoints for uploading."""

# DEPOSIT_PID_MINTER = "recid"
# """PID minter used for record submissions."""

DEPOSIT_JSONSCHEMAS_PREFIX = "deposits/"
# """Prefix for all deposit JSON schemas."""

DEPOSIT_REST_FACETS = {
    "deposits": {
        "aggs": {
            "status": {
                "terms": {"field": "_deposit.status"},
            },
        },
        "post_filters": {
            "status": terms_filter("_deposit.status"),
        },
    },
}
"""Basic deposit facts configuration.
See :data:`invenio_records_rest.config.RECORDS_REST_FACETS` for more
information.
"""

DEPOSIT_UI_TOMBSTONE_TEMPLATE = "invenio_deposit/tombstone.html"
# """Template for a tombstone deposit page."""


DEPOSIT_DEFAULT_STORAGE_CLASS = "S"
# """Default storage class."""
