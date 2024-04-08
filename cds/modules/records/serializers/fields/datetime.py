# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
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

"""Date string field."""

from __future__ import absolute_import, print_function

import arrow
from arrow.parser import ParserError
from marshmallow import fields, missing


class DateString(fields.Date):
    """ISO8601-formatted date string."""

    def _serialize(self, value, attr, obj):
        """Serialize an ISO8601-formatted date."""
        try:
            return super(DateString, self)._serialize(
                arrow.get(value).date(), attr, obj
            )
        except ParserError:
            return missing

    def _deserialize(self, value, attr, data, **kwargs):
        """Deserialize an ISO8601-formatted date."""
        return super(DateString, self)._deserialize(value, attr, data).isoformat()
