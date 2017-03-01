# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""DataCite record and fields schemas."""

from __future__ import absolute_import, print_function

import arrow

from marshmallow import Schema, fields


class IdentifierSchema(Schema):
    """Identifier schema."""

    identifier = fields.Function(lambda o: o)
    identifierType = fields.Constant('DOI')


class TitleSchema(Schema):
    """Title schema."""

    title = fields.Str(attribute='title')


class DateSchema(Schema):
    """Date schema."""

    date = fields.Str(attribute='date')
    dateType = fields.Str(attribute='type')


class DataCiteSchemaV1(Schema):
    """DataCite schema v1."""

    creators = fields.Method('get_creators')
    dates = fields.Method('get_dates')
    descriptions = fields.Method('get_descriptions')
    identifier = fields.Nested(IdentifierSchema, attribute='metadata.doi')
    language = fields.Str(attribute='metadata.language')
    publicationYear = fields.Method('get_publication_year')
    publisher = fields.Constant('CERN')
    resourceType = fields.Method('get_resource_type')
    subjects = fields.Method('get_subjects')
    titles = fields.List(
        fields.Nested(TitleSchema), attribute='metadata.title')

    def get_resource_type(self, obj):
        """Get resource type."""
        return {
            'resourceType': None,
            'resourceTypeGeneral': 'video',
        }

    def get_subjects(self, obj):
        """Get subjects."""
        items = []
        for s in obj['metadata'].get('keywords', []):
            value = s.get('value')
            if value:
                items.append({'subject': value})
        return items

    def get_descriptions(self, obj):
        """Get descriptions."""
        items = []
        desc = obj['metadata'].get('description', []).get('value')
        if desc:
            items.append({
                'description': desc,
                'descriptionType': 'Abstract',
            })
        return items

    def get_creators(self, obj):
        """Get creators."""
        items = []
        for item in obj['metadata'].get('contributors', []):
            items.append({
                'creatorName': item.get('name', ''),
            })
        return items

    #  def get_contributors(self, obj):
    #      """Get contributors."""
    #      items = []
    #      for item in obj['metadata'].get('contributors', []):
    #          items.append({
    #              'contributorType': item.get('role', ''),
    #              'contributorName': item.get('name', ''),
    #              # FIXME nameIdentifier and nameIdentifierScheme, ... ?
    #          })
    #      return items

    def get_publication_year(self, obj):
        """Get publication year."""
        return str(arrow.get(obj['metadata']['publication_date']).year)

    def get_dates(self, obj):
        """Get dates."""
        s = DateSchema()
        return [s.dump({
            'date': obj['metadata']['publication_date'],
            'type': 'Published',
        }).data]
