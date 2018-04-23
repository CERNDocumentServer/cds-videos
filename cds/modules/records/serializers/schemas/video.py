# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2018 CERN.
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
"""Video JSON schema."""

from __future__ import absolute_import

from invenio_jsonschemas import current_jsonschemas
from marshmallow import Schema, fields, post_load

from ....deposit.api import Video
from ..fields.datetime import DateString
from .common import (AccessSchema, BucketSchema, ContributorSchema,
                     DepositSchema, ExternalSystemIdentifiersField,
                     KeywordsSchema, LicenseSchema, OaiSchema,
                     RelatedLinksSchema, StrictKeysSchema, TitleSchema,
                     TranslationsSchema)
from .doi import DOI


class _CDSSSchema(Schema):
    """CDS private metadata."""

    state = fields.Raw()
    extracted_metadata = fields.Raw()
    modified_by = fields.Int()


class VideoDepositSchema(DepositSchema):
    """Project Deposit Schema."""

    id = fields.Str(required=True)


class CopyrightSchema(StrictKeysSchema):
    """Copyright schema."""

    holder = fields.Str()
    url = fields.Str()
    year = fields.Str()


class VideoFileSchema(StrictKeysSchema):
    """Video file schema."""

    bitrate = fields.Str()
    bucket = fields.Str()
    category = fields.Str()
    checksum = fields.Str()
    height = fields.Str()
    key = fields.Str()
    previewer = fields.Str()
    quality = fields.Str()
    size = fields.Integer()
    thumbnail = fields.Str()
    type = fields.Str()
    version_id = fields.Str()
    width = fields.Str()


class AcceleratorExperimentSchema(StrictKeysSchema):
    """Field accelerator_experiment."""

    project = fields.Str()
    study = fields.Str()
    experiment = fields.Str()
    accelerator = fields.Str()
    facility = fields.Str()


class PhysicalMediumSchema(StrictKeysSchema):
    """Field physical medium."""

    arrangement = fields.Str()
    bar_code = fields.Str()
    camera = fields.Str()
    copy_number = fields.Str()
    internal_note = fields.Str()
    location = fields.Str()
    medium_standard = fields.Str()
    note = fields.Str()
    sequence_number = fields.Str()
    shelf = fields.Str()


class VideoSchema(StrictKeysSchema):
    """Video schema."""

    _access = fields.Nested(AccessSchema)
    _buckets = fields.Nested(BucketSchema)
    _cds = fields.Nested(_CDSSSchema, required=True)
    _deposit = fields.Nested(VideoDepositSchema, required=True)
    _oai = fields.Nested(OaiSchema)
    _project_id = fields.Str()
    accelerator_experiment = fields.Nested(AcceleratorExperimentSchema)
    agency_code = fields.Str()
    category = fields.Str()
    contributors = fields.Nested(ContributorSchema, many=True, required=True)
    copyright = fields.Nested(CopyrightSchema)
    date = DateString(required=True)
    description = fields.Str(required=True)
    doi = DOI()
    duration = fields.Str()
    external_system_identifiers = fields.Nested(
        ExternalSystemIdentifiersField, many=True)
    featured = fields.Boolean()
    internal_note = fields.Str()
    internal_categories = fields.Raw()
    Press = fields.List(fields.Str, many=True)
    keywords = fields.Nested(KeywordsSchema, many=True)
    language = fields.Str()
    license = fields.Nested(LicenseSchema, many=True)
    note = fields.Str()
    publication_date = fields.Str()
    recid = fields.Number()
    related_links = fields.Nested(RelatedLinksSchema, many=True)
    report_number = fields.List(fields.Str, many=True)
    schema = fields.Str(attribute="$schema", dump_to='$schema')
    title = fields.Nested(TitleSchema, required=True)
    translations = fields.Nested(TranslationsSchema, many=True)
    type = fields.Str()
    vr = fields.Boolean()

    # Preservation fields
    location = fields.Str()
    original_source = fields.Str()
    physical_medium = fields.Nested(PhysicalMediumSchema, many=True)

    @post_load(pass_many=False)
    def post_load(self, data):
        """Post load."""
        data['$schema'] = current_jsonschemas.path_to_url(Video._schema)
        return data
