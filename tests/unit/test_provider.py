# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Unit tests for record minters."""


from uuid import uuid4

import mock
import pytest
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from cds.modules.records.minters import cds_record_minter, is_local_doi


def test_recid_provider(db):
    """Test the CDS recid provider using random uuid for the record."""
    with mock.patch("requests.get") as httpmock, mock.patch(
        "invenio_pidstore.models.PersistentIdentifier.create"
    ) as pid_create:
        pid_create.configure_mock(
            **{"return_value.pid_provider": None, "return_value.pid_value": 1}
        )
        httpmock.return_value.text = "1"

        data = dict()
        uuid = uuid4()
        cds_record_minter(uuid, data)

        assert data["recid"] == 1
        pid_create.assert_any_call(
            "recid",
            "1",
            pid_provider=None,
            object_type="rec",
            object_uuid=uuid,
            status=PIDStatus.REGISTERED,
        )
        pid_create.assert_any_call(
            "doi",
            "10.0000/videos.1",
            object_type="rec",
            object_uuid=uuid,
            pid_provider="datacite",
            status=PIDStatus.RESERVED,
        )


@pytest.mark.parametrize(
    "doi_in, doi_out",
    [
        # ('10.1234/foo', '10.1234/foo'),
        # ('10.5072/foo', '10.5072/foo'),
        (None, "10.0000/videos.1"),
    ],
)
def test_doi_minting(db, doi_in, doi_out):
    """Test using same integer for dep/rec ids."""
    rec_uuid = uuid4()
    data = dict(doi=doi_in)
    cds_record_minter(rec_uuid, data)
    db.session.commit()

    pid = PersistentIdentifier.get("doi", doi_out)
    assert pid.object_uuid == rec_uuid
    assert pid.status == PIDStatus.RESERVED


@pytest.mark.parametrize(
    "doi",
    [
        "batman/superman",
        "jessica/jones",
    ],
)
def test_invalid_doi(db, doi):
    """Test invalid doi."""
    uuid = uuid4()
    data = dict(doi=doi)
    with pytest.raises(AssertionError):
        cds_record_minter(uuid, data)


def test_no_doi_minted_for_projects(db, api_project):
    """Test that the DOI is not minted for Project."""
    (project, video_1, video_2) = api_project
    uuid1 = uuid4()
    uuid2 = uuid4()
    cds_record_minter(uuid1, project)
    # Project shouldn't have a DOI
    assert project.get("doi") is None
    cds_record_minter(uuid2, video_1)
    # Video should have a DOI
    assert video_1.get("doi")


def test_recid_provider_exception(db):
    """Test if providing a recid will cause an error."""
    with pytest.raises(AssertionError):
        cds_record_minter("12345678123456781234567812345678", dict({"recid": 1}))


def test_minting_recid(db):
    """Test reminting doi for published record."""
    data = dict()
    # Assert registration of recid.
    rec_uuid = uuid4()
    pid = cds_record_minter(rec_uuid, data)
    assert pid.pid_type == "recid"
    assert pid.pid_value == "1"
    assert pid.status == PIDStatus.REGISTERED
    assert pid.object_uuid == rec_uuid
    assert data["doi"] == "10.0000/videos.1"
    with pytest.raises(AssertionError):
        cds_record_minter(rec_uuid, data)


def test_is_local_doi(app):
    """Test is local."""
    doi_1 = app.config["PIDSTORE_DATACITE_DOI_PREFIX"]
    assert is_local_doi("{0}/123".format(doi_1)) is True
    for doi in app.config["CDS_LOCAL_DOI_PREFIXES"]:
        assert is_local_doi("{0}/123".format(doi)) is True
    assert is_local_doi("test/doi") is False
