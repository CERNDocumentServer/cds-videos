# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Persistent identifier fetcher."""


from invenio_pidstore.fetchers import FetchedPID

from .providers import CDSRecordIdProvider, CDSReportNumberProvider


def recid_fetcher(record_uuid, data):
    """Fetch PID from record."""
    return FetchedPID(
        provider=CDSRecordIdProvider,
        pid_type="recid",
        pid_value=str(data["recid"]),
    )


def report_number_fetcher(record_uuid, data):
    """Fetch report number."""
    return FetchedPID(
        provider=CDSReportNumberProvider,
        pid_type="rn",
        pid_value=str(data["report_number"][0]),
    )


def doi_fetcher(record_uuid, data):
    """Fetch DOI."""
    return FetchedPID(provider=None, pid_type="doi", pid_value=str(data["doi"]))


def kwid_fetcher(record_uuid, data):
    """Fetch PID from keyword record."""
    return FetchedPID(provider=None, pid_type="kwid", pid_value=str(data["key_id"]))


def catid_fetcher(record_uuid, data):
    """Fetch PID from category record."""
    return FetchedPID(provider=None, pid_type="catid", pid_value=str(data["name"]))
