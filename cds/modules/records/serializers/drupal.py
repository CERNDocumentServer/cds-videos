# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# CDS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CDS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""Drupal serializer for records."""

from __future__ import absolute_import, print_function

import arrow
from arrow.parser import ParserError
from invenio_records_rest.serializers.json import JSONSerializer

from ...deposit.api import Project, Video
from ..api import CDSFileObject


def format_datetime(datetime):
    """Get datetime formatted."""
    try:
        return arrow.get(datetime or '').strftime('%Y-%m-%d')
    except ParserError:
        return ''


class VideoDrupal(object):
    """Video converter into drupal format."""

    def __init__(self, record):
        """Init video drupal."""
        self._record = record

    def format(self):
        """Format video."""
        record = self._record
        entry = {
            'caption_en': record.get('description', {}).get('value', ''),
            'caption_fr': self.get_translation('description', 'value', 'fr'),
            'copyright_date': record.get('copyright', {}).get('year', ''),
            'copyright_holder': record.get('copyright', {}).get('holder', ''),
            'creation_date': self.creation_date,
            'directors': self.contributors('Director'),
            'entry_date': format_datetime(record['date']),
            'id': record['report_number']['report_number'],
            'keywords': self.keywords,
            'license_body': record.get('license', [{}])[0].get('license', ''),
            'license_url': record.get('license', [{}])[0].get('url', ''),
            'producer': self.contributors('Producer'),
            'record_id': record['_deposit']['pid']['value'],
            'thumbnail': self.thumbnail,
            'title_en': record.get('title', {}).get('title', ''),
            'title_fr': self.get_translation('title', 'title', 'fr'),
            'type': self.type_,
            'video_length': self.video_length,
        }
        return {'entries': [{'entry': entry}]}

    def get_translation(self, field_name, subfield_name, lang_code):
        """Get title france."""
        titles = list(filter(
            lambda t: t.get('language') == lang_code,
            self._record.get('{0}_translations'.format(field_name), [])))
        if len(titles) != 0:
            return titles[0][subfield_name]
        return ''

    @property
    def video_length(self):
        """Get video length."""
        return self._record['duration']

    @property
    def creation_date(self):
        """Get creation date."""
        return format_datetime(self._record.get('publication_date'))

    def contributors(self, name):
        """Get the name of a type of contributors."""
        roles = filter(lambda x: x['role'] == name,
                       self._record.get('contributors', {}))
        return ", ".join([role['name'] for role in roles])

    @property
    def thumbnail(self):
        """Get thumbnail."""
        frame = self._record.get('_files', [{}])[0].get('frame', [{}])[0]
        if frame:
            return CDSFileObject._link(
                bucket_id=frame['bucket_id'], key=frame['key'], _external=True)

    @property
    def type_(self):
        """Get type."""
        if self._record['$schema'] == Video.get_record_schema():
            return 'video'
        if self._record['$schema'] == Project.get_record_schema():
            return 'project'
        return ''

    @property
    def keywords(self):
        """Get keywords."""
        keywords = self._record.get('keywords', [])
        return ", ".join([keyword['name'] for keyword in keywords])


class DrupalSerializer(JSONSerializer):
    """Drupal serializer for records."""

    def transform_record(self, pid, record, links_factory=None):
        """Serialize record for drupal."""
        if record['$schema'] == Video.get_record_schema():
            return VideoDrupal(record=record).format()
        return {}
