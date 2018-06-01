# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017 CERN.
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
"""Project JSON schema."""

from __future__ import absolute_import

from marshmallow import fields, post_load, Schema
from invenio_jsonschemas import current_jsonschemas

from ....deposit.api import Project, deposit_video_resolver
from .common import \
    AccessSchema, BucketSchema, ContributorSchema, \
    DepositSchema, ExternalSystemIdentifiersField, LicenseSchema, \
    OaiSchema, StrictKeysSchema, TitleSchema, \
    TranslationsSchema, KeywordsSchema
from .doi import DOI


class _CDSSSchema(Schema):
    """CDS private metadata."""

    state = fields.Raw()
    modified_by = fields.Int()


class ProjectDepositSchema(DepositSchema):
    """Project Deposit Schema."""

    id = fields.Str(required=True)


class FileSchema(StrictKeysSchema):
    """File schema."""

    bucket = fields.Str()
    category = fields.Str()
    checksum = fields.Str()
    key = fields.Str()
    previewer = fields.Str()
    size = fields.Integer()
    type = fields.Str()
    version_id = fields.Str()


class ProjectSchema(StrictKeysSchema):
    """Project schema."""

    _deposit = fields.Nested(ProjectDepositSchema, required=True)
    _cds = fields.Nested(_CDSSSchema, required=True)
    title = fields.Nested(TitleSchema, required=True)
    description = fields.Str()
    category = fields.Str(required=True)
    type = fields.Str(required=True)
    note = fields.Str()

    recid = fields.Number()
    _access = fields.Nested(AccessSchema)
    _buckets = fields.Nested(BucketSchema)
    _oai = fields.Nested(OaiSchema)
    _eos_library_path = fields.Str()
    contributors = fields.Nested(ContributorSchema, many=True, required=True)
    doi = DOI()
    keywords = fields.Nested(KeywordsSchema, many=True)
    license = fields.Nested(LicenseSchema, many=True)
    schema = fields.Str(attribute='$schema', dump_to='$schema')
    videos = fields.Method(deserialize='get_videos_refs')
    translations = fields.Nested(TranslationsSchema, many=True)
    report_number = fields.List(fields.Str, many=True)
    publication_date = fields.Str()
    external_system_identifiers = fields.Nested(
        ExternalSystemIdentifiersField, many=True)


    @post_load(pass_many=False)
    def post_load(self, data):
        """Post load."""
        data['$schema'] = current_jsonschemas.path_to_url(Project._schema)
        return data

    def get_videos_refs(self, obj):
        """Get videos references."""
        return [Project.build_video_ref(
            deposit_video_resolver(o['_deposit']['id'])
        ) for o in obj]
