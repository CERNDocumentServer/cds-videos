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
from marshmallow_utils.fields import SanitizedHTML
from marshmallow_utils.html import sanitize_html

from ...api import Keyword
from ...resolver import keyword_resolver
from ..fields.datetime import DateString


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
    source = fields.Str()

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
    description = SanitizedHTML()
    language = fields.Str()


class RelatedLinksSchema(StrictKeysSchema):
    """Translations schema."""

    name = fields.Str()
    url = fields.Str()


class ExternalSystemIdentifiersField(StrictKeysSchema):
    """Field physical medium."""

    value = fields.Str()
    schema = fields.Str()


class AlternateIdentifiersSchema(StrictKeysSchema):
    """Field alternate_identifiers."""

    value = fields.Str(required=True)
    scheme = fields.Str(required=True)


class LegacyMARCFieldsSchema(Schema):
    tag_964 = fields.List(fields.Str(), data_key="964")
    tag_336 = fields.List(fields.Str(), data_key="336")
    tag_583 = fields.List(fields.Str(), data_key="583")
    tag_306 = fields.List(fields.Str(), data_key="306")
    tag_088 = fields.List(fields.Str(), data_key="088")


class DigitizedMetadataSchema(Schema):
    url = fields.Str()
    format = fields.Str()
    link_text = fields.Str()
    public_note = fields.Str()
    nonpublic_note = fields.Str()
    md5_checksum = fields.Str()
    source = fields.Str()


class CurationSchema(StrictKeysSchema):
    """Curation schema."""

    legacy_report_number = fields.List(fields.Str())
    legacy_dates = fields.List(DateString())
    department = fields.Str()
    volumes = fields.List(fields.Str())
    physical_location = fields.List(fields.Str())
    physical_medium = fields.List(fields.Str())
    internal_note = fields.List(fields.Str())
    legacy_marc_fields = fields.Nested(LegacyMARCFieldsSchema)
    digitized = fields.Nested(DigitizedMetadataSchema)


class AdditionalTitlesSchema(Schema):
    """Additional titles schema."""

    title = fields.Str()
    type = fields.Str()
    lang = fields.Str()


class AdditionalDescriptionsSchema(Schema):
    """Additional descriptions schema."""

    description = fields.Str()
    type = fields.Str()
    lang = fields.Str()


class RelatedIdentifiersSchema(Schema):
    identifier = fields.Str(required=True)
    scheme = fields.Str(required=True)
    relation_type = fields.Str(required=True)
    resource_type = fields.Str()


class SanitizedHTMLWithCSS(fields.String):
    """Enhanced SanitizedHTML supporting inline CSS sanitization.

    Fully compatible with marshmallow_utils.fields.SanitizedHTML,
    but adds CSS.
    """

    def __init__(
        self,
        tags=None,
        attrs=None,
        css_styles=None,
        *args,
        **kwargs,
    ):
        """
        :param tags: Allowed HTML tags.
        :param attrs: Allowed HTML attributes per tag.
        :param css_styles: List of allowed CSS properties (e.g., ["color"]).
        """
        super().__init__(*args, **kwargs)

        self.tags = tags
        self.attrs = attrs
        self.css_styles = css_styles

    def _deserialize(self, value, attr, data, **kwargs):
        """Run bleach sanitize with CSS support."""
        value = super()._deserialize(value, attr, data, **kwargs)

        return sanitize_html(
            value,
            tags=self.tags,
            attrs=self.attrs,
            css_styles=self.css_styles,
        )
