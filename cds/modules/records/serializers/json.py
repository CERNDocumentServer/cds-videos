# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017, 2018 CERN.
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
"""CDS JSON Serializer."""

from __future__ import absolute_import, print_function

from flask import has_request_context
from flask_security import current_user
from invenio_records_rest.serializers.json import JSONSerializer

from ..api import CDSRecord
from ..permissions import (has_read_record_eos_path_permission,
                           has_read_record_permission)
from ..utils import HTMLTagRemover, remove_html_tags


class CDSJSONSerializer(JSONSerializer):
    """CDS JSON serializer.

    Adds or removes fields  depending on access rights.
    """
    html_tag_remover = HTMLTagRemover()

    def preprocess_record(self, pid, record, links_factory=None):
        """Include ``_eos_library_path`` for single record retrievals."""
        result = super(CDSJSONSerializer, self).preprocess_record(
            pid, record, links_factory=links_factory
        )
        # Add/remove files depending on access right.
        if isinstance(record, CDSRecord):
            metadata = result['metadata']
            if '_eos_library_path' in record and (not has_request_context() or
                not has_read_record_eos_path_permission(current_user, record)):
                metadata.pop('_eos_library_path')

            # sanitize title by unescaping and stripping html tags
            try:
                title = metadata['title']['title']
                title = self.html_tag_remover.unescape(title)
                metadata['title']['title'] = remove_html_tags(
                    self.html_tag_remover, title)

                # decode html entities
                metadata['description'] = self.html_tag_remover.unescape(
                    metadata['description'])
                if has_request_context():
                    metadata['videos'] = [
                        video for video in metadata['videos']
                        if has_read_record_permission(current_user, video)
                    ]
            except KeyError:
                # ignore error if keys are missing in the metadata
                pass

        return result

    def preprocess_search_hit(self, pid, record_hit, links_factory=None):
        """Prepare a record hit from Elasticsearch for serialization."""
        # do not pass links_factory when fetching data from ES, otherwise it
        # will load the record from db for each search result
        # see: cds.modules.records.links.record_link_factory
        result = super(CDSJSONSerializer, self).preprocess_search_hit(
            pid, record_hit)

        if 'metadata' in result:
            metadata = result['metadata']

            try:
                title = metadata['title']['title']
                title = self.html_tag_remover.unescape(title)
                metadata['title']['title'] = remove_html_tags(
                    self.html_tag_remover, title)

                metadata['description'] = self.html_tag_remover.unescape(
                    metadata['description'])
            except KeyError:
                # ignore error if keys are missing in the metadata
                pass

        return result
