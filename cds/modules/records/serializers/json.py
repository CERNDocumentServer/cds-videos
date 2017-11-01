# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
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
from ..permissions import has_read_record_eos_path_permission


class CDSJSONSerializer(JSONSerializer):
    """CDS JSON serializer.

    Adds or removes fields  depending on access rights.
    """

    def preprocess_record(self, pid, record, links_factory=None):
        """Include ``_eos_library_path`` for single record retrievals."""
        result = super(CDSJSONSerializer, self).preprocess_record(
            pid, record, links_factory=links_factory
        )
        # Add/remove files depending on access right.
        if isinstance(record, CDSRecord) and '_eos_library_path' in record:
            if not has_request_context() or not has_read_record_eos_path_permission(
                    current_user, record):
                result['metadata'].pop('_eos_library_path')
        return result
