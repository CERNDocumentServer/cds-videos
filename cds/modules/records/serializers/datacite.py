# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2024 CERN.
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

"""VTT serializer for records."""

from invenio_records_rest.serializers.datacite import DataCite41Serializer


class CDSDataCite41Serializer(DataCite41Serializer):
    """Drupal serializer for records."""

    def dump(self, obj, context=None):
        """Serialize object with schema."""
        return self.schema_class(context=context).dump(obj)
