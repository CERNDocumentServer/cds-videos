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

"""Project JSON schema."""

from __future__ import absolute_import

from cds.modules.records.serializers.schemas.json.common import \
    StrictKeysSchema, AccessSchema, DescriptionSchema, KeywordsSchema, \
    ContributorSchema, TitleTranslationSchema, OaiSchema, \
    DescriptionTranslationSchema, DepositSchema, CreatorSchema, TitleSchema, \
    BucketSchema, ReportNumberSchema, LicenseSchema
from marshmallow import fields


class ProjectDepositSchema(DepositSchema):
    """Project Deposit Schema."""

    state = fields.Raw()


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


class ProjectVideoSchema(StrictKeysSchema):
    """Video schema."""

    reference = fields.Str(attribute='$reference')


class ProjectSchema(StrictKeysSchema):
    """Project schema."""

    _access = fields.Nested(AccessSchema)
    _buckets = fields.Nested(BucketSchema)
    _deposit = fields.Nested(ProjectDepositSchema)
    _oai = fields.Nested(OaiSchema)
    category = fields.Str()
    type = fields.Str()
    contributors = fields.Nested(ContributorSchema, many=True)
    creator = fields.Nested(CreatorSchema)
    date = fields.Str()
    description = fields.Nested(DescriptionSchema)
    description_translations = fields.Nested(DescriptionTranslationSchema,
                                             many=True)
    keywords = fields.Nested(KeywordsSchema, many=True)
    license = fields.Nested(LicenseSchema, many=True)
    recid = fields.Number()
    schema = fields.Str(attribute='$schema')
    title = fields.Nested(TitleSchema)
    title_translations = fields.Nested(TitleTranslationSchema, many=True)
    videos = fields.Nested(ProjectVideoSchema, many=True)

    category = fields.Str()
    type = fields.Str()
    report_number = fields.Nested(ReportNumberSchema, many=False)
