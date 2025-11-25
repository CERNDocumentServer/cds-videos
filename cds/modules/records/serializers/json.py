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


from flask import has_request_context
from flask_security import current_user
from invenio_records_rest.serializers.json import JSONSerializer

from ..api import CDSRecord
from ..permissions import (
    has_read_record_eos_path_permission,
    has_read_record_permission,
)
from ..utils import HTMLTagRemover, parse_video_chapters, remove_html_tags
from marshmallow_utils.html import sanitize_html, ALLOWED_HTML_ATTRS, ALLOWED_CSS_STYLES

CUSTOM_ALLOWED_ATTRS = {
    **ALLOWED_HTML_ATTRS,
    "span": ALLOWED_HTML_ATTRS.get("span", []) + ["style"],
    "p": ALLOWED_HTML_ATTRS.get("p", []) + ["style"],
}

CUSTOM_ALLOWED_CSS = ALLOWED_CSS_STYLES + ["color"]


class CDSJSONSerializer(JSONSerializer):
    """CDS JSON serializer.

    Adds or removes fields  depending on access rights.
    """

    html_tag_remover = HTMLTagRemover()

    def dump(self, obj, context=None):
        """Serialize object with schema."""
        return self.schema_class(context=context).dump(obj)

    def _sanitize_metadata(self, metadata):
        """Sanitize title, description and translations in metadata."""
        try:
            if "title" in metadata and "title" in metadata["title"]:
                title = metadata["title"]["title"]
                title = self.html_tag_remover.unescape(title)
                metadata["title"]["title"] = remove_html_tags(
                    self.html_tag_remover, title
                )

            if "description" in metadata:
                description = metadata["description"]
                description = self.html_tag_remover.unescape(description)
                metadata["description"] = sanitize_html(
                    description,
                    attrs=CUSTOM_ALLOWED_ATTRS,
                    css_styles=CUSTOM_ALLOWED_CSS,
                )

            if "translations" in metadata:
                for t in metadata["translations"]:
                    if "title" in t and "title" in t["title"]:
                        t_title = t["title"]["title"]
                        t_title = self.html_tag_remover.unescape(t_title)
                        t["title"]["title"] = remove_html_tags(
                            self.html_tag_remover, t_title
                        )

                    if "description" in t:
                        t_desc = t["description"]
                        t_desc = self.html_tag_remover.unescape(t_desc)
                        t["description"] = sanitize_html(t_desc)

        except KeyError:
            # ignore error if keys are missing
            pass

        return metadata

    def preprocess_record(self, pid, record, links_factory=None):
        """Include ``_eos_library_path`` for single record retrievals."""
        result = super(CDSJSONSerializer, self).preprocess_record(
            pid, record, links_factory=links_factory
        )
        # Add/remove files depending on access right.
        if isinstance(record, CDSRecord):
            metadata = result["metadata"]
            if "_eos_library_path" in record and (
                not has_request_context()
                or not has_read_record_eos_path_permission(current_user, record)
            ):
                metadata.pop("_eos_library_path")

            # sanitize title by unescaping and stripping html tags
            try:
                metadata = self._sanitize_metadata(metadata)
                if has_request_context():
                    metadata["videos"] = [
                        video
                        for video in metadata["videos"]
                        if has_read_record_permission(current_user, video)
                    ]
            except KeyError:
                # ignore error if keys are missing in the metadata
                pass

            description = metadata.get("description", "")
            if description:
                metadata["chapters"] = parse_video_chapters(description)
            else:
                metadata["chapters"] = []

        return result

    def preprocess_search_hit(self, pid, record_hit, links_factory=None):
        """Prepare a record hit from opensearch for serialization."""
        # do not pass links_factory when fetching data from ES, otherwise it
        # will load the record from db for each search result
        # see: cds.modules.records.links.record_link_factory
        result = super(CDSJSONSerializer, self).preprocess_search_hit(pid, record_hit)

        if "metadata" in result:
            metadata = result["metadata"]
            result["metadata"] = self._sanitize_metadata(result["metadata"])

        return result
