# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS migration to CDSLabs tests."""

from __future__ import absolute_import, print_function

from os.path import join

from click.testing import CliRunner
from invenio_migrator.proxies import current_migrator
from invenio_records.models import RecordMetadata
from invenio_records import Record
from invenio_pidstore.resolver import Resolver

from cds.cli import cli


def test_record_files_migration(app, location, script_info, datadir):
    """Test CDS records and files migrations."""
    runner = CliRunner()
    filepath = join(datadir, 'cds_records_and_files_dump.json')

    result = runner.invoke(
        cli, ['dumps', 'loadrecords', filepath], obj=script_info)
    assert result.exit_code == 0

    assert RecordMetadata.query.count() == 1

    # CERN Theses
    resolver = Resolver(
        pid_type='recid', object_type='rec', getter=Record.get_record)
    pid, record = resolver.resolve(1198695)

    assert record
    assert record.revision_id == 34  # 33 from the dump and 1 for the files
    assert record['main_entry_personal_name']['personal_name'] == 'Caffaro, J'
    assert 'CERN' in record['subject_indicator']
    assert record['control_number'] == '1198695'
    assert record['title_statement']['title'] == \
        'Improving the Formatting Tools of CDS Invenio'
    assert record['source_of_acquisition'][0]['stock_number'] == \
        'CERN-THESIS-2009-057'

    assert '_files' in record
    assert record['_files'][0]['key'] == 'CERN-THESIS-2009-057.pdf'
