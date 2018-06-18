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

"""Persistent identifier minters."""

from __future__ import absolute_import, print_function

import idutils

from flask import current_app

from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from .providers import CDSRecordIdProvider, CDSReportNumberProvider


def cds_record_minter(record_uuid, data):
    """Mint record identifiers."""
    provider = _rec_minter(record_uuid, data)

    from .permissions import is_public
    from cds.modules.deposit.api import Project
    project_schema = current_jsonschemas.path_to_url(Project._schema)

    # We shouldn't mint the DOI for the project (CDS#996)
    if data.get('$schema') != project_schema and is_public(data, 'read'):
        doi_minter(record_uuid, data)

    return provider.pid


def report_number_minter(record_uuid, data, **kwargs):
    """Mint report number."""
    assert 'report_number' not in data
    provider = CDSReportNumberProvider.create(
        object_type='rec', object_uuid=record_uuid, data=data, **kwargs)
    data['report_number'] = [provider.pid.pid_value]
    return provider.pid.pid_value


def cds_doi_generator(recid, prefix=None):
    """Generate a DOI."""
    return '{prefix}/cds.{recid}'.format(
        prefix=prefix or current_app.config['PIDSTORE_DATACITE_DOI_PREFIX'],
        recid=recid
    )


def _rec_minter(record_uuid, data):
    """Record minter."""
    assert 'recid' not in data
    provider = CDSRecordIdProvider.create(
        object_type='rec', object_uuid=record_uuid)
    data['recid'] = int(provider.pid.pid_value)
    return provider


def doi_minter(record_uuid, data):
    """Mint DOI."""
    doi = data.get('doi')
    assert 'recid' in data
    assert idutils.is_doi(doi) if doi else True
    
    # Create a DOI if no DOI was found.
    if not doi:
        doi = cds_doi_generator(data['recid'])
        data['doi'] = doi

        # Make sure it's a proper DOI
        assert idutils.is_doi(doi)
        return PersistentIdentifier.create(
            'doi',
            doi,
            pid_provider='datacite',
            object_type='rec',
            object_uuid=record_uuid,
            status=PIDStatus.RESERVED
        )


def is_local_doi(doi):
    """Check if DOI is a locally managed DOI."""
    prefixes = [
        current_app.config['PIDSTORE_DATACITE_DOI_PREFIX']
    ] + current_app.config['CDS_LOCAL_DOI_PREFIXES']
    for p in prefixes:
        if doi.startswith('{0}/'.format(p)):
            return True
    return False


def kwid_minter(record_uuid, data):
    """Mint category identifiers."""
    return PersistentIdentifier.create(
        'kwid',
        data['key_id'],
        object_type='rec',
        object_uuid=record_uuid,
        status=PIDStatus.REGISTERED
    )


def catid_minter(record_uuid, data):
    """Mint category identifiers."""
    return PersistentIdentifier.create(
        'catid',
        data['name'],
        object_type='rec',
        object_uuid=record_uuid,
        status=PIDStatus.REGISTERED
    )
