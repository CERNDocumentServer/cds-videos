# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
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

"""Test cds package."""

from __future__ import absolute_import, print_function
from flask import url_for
from invenio_records_ui import InvenioRecordsUI
from invenio_pidstore.providers.recordid import RecordIdProvider

import json


import mock
import pytest

from cds.modules.records.views import records_ui_export


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_ui_export(app, project_published):
    """Test view."""
    (project, video_1, video_2) = project_published
    pid = project['_deposit']['pid']['value']
    with app.test_client() as client:
        # Test that default view function can deal with multiple parameters.
        res = client.get('/record/' + pid + '/export/blabla')
        assert res.status_code == 404
        res = client.get('/record/' + pid + '/export/json')
        assert res.status_code == 200
        # Test that actual data has been exported (not blank)
        data_start = res.data.find(b'<pre>') + 5
        data_end = res.data.find(b'</pre>', data_start)
        data = res.data[data_start:data_end]
        assert len(data) > 1
