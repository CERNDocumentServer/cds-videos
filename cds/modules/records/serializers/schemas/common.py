# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Common JSON schemas."""

from marshmallow import RAISE, Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Length

from ...api import Keyword
from ...resolver import keyword_resolver


class LicenseSchema(Schema):
    """License schema."""

    license = fields.Str()
    material = fields.Str()
    credit = fields.Str()
    url = fields.Str()


class StrictKeysSchema(Schema):
    """Ensure only valid keys exists."""

    class Meta:
        unknown = RAISE


class KeywordsSchema(Schema):
    """Keywords schema."""

    name = fields.Str()
    value = fields.Dict()

    @validates_schema
    def validate_keyword_schema(self, data, **kwargs):
        """Validates that either id either the free text field are present."""
        key_id = data.get("value", {}).get("key_id")
        free_text = data.get("name")

        # remove value
        data.pop("value", None)

        if key_id:
            try:
                keyword_resolver.resolve(key_id)
            except:
                raise ValidationError("One or more keywords not resolvable.")

        if not key_id and not free_text:
            raise ValidationError(
                "An existing key_id or a free text name must be present."
            )


class OaiSchema(StrictKeysSchema):
    """Oai schema."""

    id = fields.Str()
    sets = fields.List(fields.Str())
    updated = fields.Str()


class PidSchema(StrictKeysSchema):
    """Pid schema."""

    revision_id = fields.Integer()
    type = fields.Str()
    value = fields.Str()


class IdsSchema(StrictKeysSchema):
    """Ids schema."""

    source = fields.Str()
    value = fields.Str()


class TitleSchema(StrictKeysSchema):
    """Title schema."""

    source = fields.Str()
    subtitle = fields.Str()
    title = fields.Str(required=True, allow_none=False, validate=Length(min=1))


class AccessSchema(StrictKeysSchema):
    """Access schema."""

    read = fields.List(fields.Raw(allow_none=True), allow_none=True)
    update = fields.List(fields.Raw(allow_none=True), allow_none=True)


class ContributorSchema(StrictKeysSchema):
    """Contributor schema."""

    affiliations = fields.List(fields.Str())
    contribution = fields.Str()
    email = fields.Str()
    ids = fields.Nested(IdsSchema, many=True)
    name = fields.Str(required=True)
    role = fields.Str(required=True)


class DepositSchema(StrictKeysSchema):
    """Deposit schema."""

    created_by = fields.Integer()
    id = fields.Str(allow_none=True, required=True)
    owners = fields.List(fields.Integer())
    pid = fields.Nested(PidSchema)
    status = fields.Str()


class BucketSchema(StrictKeysSchema):
    """Bucket schema."""

    deposit = fields.Str()
    record = fields.Str()


class TranslationsSchema(StrictKeysSchema):
    """Translations schema."""

    title = fields.Nested(TitleSchema)
    description = fields.Str()
    language = fields.Str()


class RelatedLinksSchema(StrictKeysSchema):
    """Translations schema."""

    name = fields.Str()
    url = fields.Str()


class ExternalSystemIdentifiersField(StrictKeysSchema):
    """Field physical medium."""

    value = fields.Str()
    schema = fields.Str()
