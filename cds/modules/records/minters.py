# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Persistent identifier minters."""

from __future__ import absolute_import, print_function

import idutils

from flask import current_app

from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from .providers import CDSRecordIdProvider


def recid_minter(record_uuid, data):
    """Mint record identifiers."""
    assert 'recid' not in data
    provider = CDSRecordIdProvider.create(
        object_type='rec', object_uuid=record_uuid)
    data['recid'] = int(provider.pid.pid_value)

    cds_doi_minter(record_uuid, data)

    return provider.pid


def cds_doi_generator(recid, prefix=None):
    """Generate a DOI."""
    return '{prefix}/cds.{recid}'.format(
        prefix=prefix or current_app.config['PIDSTORE_DATACITE_DOI_PREFIX'],
        recid=recid
)


def cds_doi_minter(record_uuid, data):
    """Mint DOI."""
    doi = data.get('doi')
    assert 'recid' in data

    # Create a DOI if no DOI was found.
    if not doi:
        doi = cds_doi_generator(data['recid'])
        data['doi'] = doi

    # Make sure it's a proper DOI
    assert idutils.is_doi(doi)
    return PersistentIdentifier.create(
        'doi',
        doi,
        object_type='rec',
        object_uuid=record_uuid,
        status=PIDStatus.RESERVED
    )

