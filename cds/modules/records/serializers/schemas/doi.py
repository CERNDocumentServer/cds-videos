# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""DOI field."""


import idutils
from invenio_i18n import lazy_gettext as _
from marshmallow import fields


class DOI(fields.String):
    """Special DOI field."""

    default_error_messages = {
        "invalid_doi": _(
            "The provided DOI is invalid - it should look similar "
            " to '10.1234/foo.bar'."
        ),
        "managed_prefix": ("The prefix {prefix} is administrated locally."),
        "banned_prefix": ("The prefix {prefix} is invalid."),
        "test_prefix": _(
            "The prefix 10.5072 is invalid. The "
            "prefix is only used for testing purposes, and no DOIs with "
            "this prefix are attached to any meaningful content."
        ),
        "required_doi": _("The DOI cannot be changed."),
    }

    def __init__(
        self,
        required_doi=None,
        allowed_dois=None,
        managed_prefixes=None,
        banned_prefixes=None,
        *args,
        **kwargs
    ):
        """Initialize field."""
        super(DOI, self).__init__(*args, **kwargs)
        self.required_doi = required_doi
        self.allowed_dois = allowed_dois
        self.managed_prefixes = managed_prefixes or []
        self.banned_prefixes = banned_prefixes or ["10.5072"]

    def _deserialize(self, value, attr, data, **kwargs):
        """Deserialize DOI value."""
        value = super(DOI, self)._deserialize(value, attr, data, **kwargs)
        value = value.strip()
        if value == "" and not (self.required or self.context.get("doi_required")):
            return value
        if not idutils.is_doi(value):
            self.make_error("invalid_doi")
        return idutils.normalize_doi(value)

    def _validate(self, value):
        """Validate DOI value."""
        super(DOI, self)._validate(value)

        required_doi = self.context.get("required_doi", self.required_doi)
        allowed_dois = self.context.get("allowed_dois", self.allowed_dois)
        managed_prefixes = self.context.get("managed_prefixes", self.managed_prefixes)
        banned_prefixes = self.context.get("banned_prefixes", self.banned_prefixes)

        # First check for required DOI.
        if required_doi:
            if value == required_doi:
                return
            self.make_error("required_doi")
        # Check if DOI is in allowed list.
        if allowed_dois:
            if value in allowed_dois:
                return

        prefix = value.split("/")[0]
        # Check for managed prefix
        if managed_prefixes and prefix in managed_prefixes:
            self.make_error("managed_prefix", prefix=prefix)
        # Check for banned prefixes
        if banned_prefixes and prefix in banned_prefixes:
            self.make_error(
                "test_prefix" if prefix == "10.5072" else "banned_prefix", prefix=prefix
            )


class DOILink(fields.Field):
    """DOI link field."""

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        return idutils.to_url(value, "doi")
