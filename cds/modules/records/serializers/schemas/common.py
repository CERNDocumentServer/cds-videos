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

from __future__ import absolute_import

from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Length

from ...api import Keyword


class LicenseSchema(Schema):
    """License schema."""

    license = fields.Str()
    material = fields.Str()
    url = fields.Str()


class StrictKeysSchema(Schema):
    """Ensure only valid keys exists."""

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data):
        """Check for unknown keys."""
        if isinstance(original_data, list):
            for elem in original_data:
                self.check_unknown_fields(data, elem)
        else:
            for key in original_data:
                if key not in [self.fields[field].attribute or field for field
                               in self.fields]:
                    raise ValidationError('Unknown field name {}'.format(key),
                                          field_names=[key])


class KeywordsSchema(Schema):
    """Keywords schema."""

    name = fields.Str()
    key_id = fields.Method(deserialize='get_keywords_refs', attribute='$ref')

    def get_keywords_refs(self, obj):
        """Get keywords references."""
        return Keyword.get_ref(id_=obj)


class OaiSchema(StrictKeysSchema):
    """Oai schema."""

    id = fields.Str()
    sets = fields.List(fields.Str())
    updated = fields.Str()


class DescriptionTranslationSchema(StrictKeysSchema):
    """Description translation schema."""

    language = fields.Str()
    source = fields.Str()
    value = fields.Str(required=True)


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
    title = fields.Str(required=True, allow_none=False, validate=Length(min=4))


class CreatorSchema(StrictKeysSchema):
    """Creator schema."""

    affiliations = fields.List(fields.Str())
    contribution = fields.Str()
    email = fields.Str()
    ids = fields.Nested(IdsSchema, many=True)
    name = fields.Str(required=True)


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


class TitleTranslationSchema(StrictKeysSchema):
    """TitleTranslation schema."""

    language = fields.Str()
    source = fields.Str()
    subtitle = fields.Str()
    title = fields.Str(required=True)


class DescriptionSchema(StrictKeysSchema):
    """Description schema."""

    source = fields.Str()
    value = fields.Str(required=True, allow_none=False, validate=Length(min=3))


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


class ReportNumberSchema(StrictKeysSchema):
    """ReportNumber schema."""

    report_number = fields.Str()
    _report_number = fields.Str()


class TranslationsSchema(StrictKeysSchema):
    """Translations schema."""

    title = fields.Nested(TitleSchema)
    description = fields.Nested(DescriptionSchema)
    language = fields.Str()


class RelatedLinksSchema(StrictKeysSchema):
    """Translations schema."""

    name = fields.Str()
    url = fields.Str()
