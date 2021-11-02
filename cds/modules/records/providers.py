# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017, 2019 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.
"""Record ID provider."""

from __future__ import absolute_import, print_function

import requests
from flask import current_app
from invenio_pidstore.errors import PersistentIdentifierError
from invenio_pidstore.models import PIDStatus
from invenio_pidstore.providers.base import BaseProvider
from invenio_pidstore.providers.recordid import RecordIdProvider


class CDSRecordIdProvider(RecordIdProvider):
    """Record identifier provider."""

    pid_type = 'recid'
    """Type of persistent identifier."""

    pid_provider = None
    """Provider name.

    The provider name is not recorded in the PID since the provider does not
    provide any additional features besides creation of record ids.
    """

    default_status = PIDStatus.RESERVED
    """Record IDs are by default registered immediately."""


class CDSReportNumberProvider(BaseProvider):
    """Report number provider."""

    pid_type = 'rn'
    """Type of persistent identifier."""

    pid_provider = None
    """Name of provider."""

    default_status = PIDStatus.RESERVED
    """Report numbers are by default registered immediately."""

    @classmethod
    def create(cls, object_type=None, object_uuid=None, data=None, **kwargs):
        """Create a new report number."""
        # assert isinstance(data, CDSDeposit)
        if 'pid_value' not in kwargs:
            sequence, kwargs = data.get_report_number_sequence(**kwargs)
            kwargs['pid_value'] = sequence.next()

        kwargs.setdefault('status', cls.default_status)
        if object_type and object_uuid:
            kwargs['status'] = PIDStatus.REGISTERED

        return super(CDSReportNumberProvider, cls).create(
            object_type=object_type, object_uuid=object_uuid, **kwargs)
