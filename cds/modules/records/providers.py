# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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
from invenio_pidstore.models import PIDStatus, RecordIdentifier
from invenio_pidstore.providers.base import BaseProvider


class CDSRecordIdProvider(BaseProvider):
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

    @classmethod
    def create(cls, object_type=None, object_uuid=None, **kwargs):
        """Create a new record identifier."""
        # Request next integer in recid sequence.
        assert 'pid_value' not in kwargs

        provider_url = current_app.config.get('RECORDS_ID_PROVIDER_ENDPOINT',
                                              None)
        if not provider_url:
            # Don't query external service in DEBUG mode
            kwargs['pid_value'] = str(RecordIdentifier.next())
        else:
            response = requests.get(
                provider_url,
                headers={
                    'User-Agent':
                    current_app.config.get('RECORDS_ID_PROVIDER_AGENT')
                })

            if not response.ok or response.text.strip().startswith('[ERROR]'):
                raise PersistentIdentifierError(response.text)

            kwargs['pid_value'] = response.text

        kwargs.setdefault('status', cls.default_status)
        if object_type and object_uuid:
            kwargs['status'] = PIDStatus.REGISTERED

        return super(CDSRecordIdProvider, cls).create(
            object_type=object_type, object_uuid=object_uuid, **kwargs)


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
        sequence, kwargs = data.get_report_number_sequence(**kwargs)
        kwargs['pid_value'] = sequence.next()

        kwargs.setdefault('status', cls.default_status)
        if object_type and object_uuid:
            kwargs['status'] = PIDStatus.REGISTERED

        return super(CDSReportNumberProvider, cls).create(
            object_type=object_type, object_uuid=object_uuid, **kwargs)
