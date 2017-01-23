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

import mock

from flask import url_for
from invenio_pidstore.providers.recordid import RecordIdProvider


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_records_ui_export(app, project_published):
    """Test view."""
    (project, video_1, video_2) = project_published
    pid = project['_deposit']['pid']['value']
    vid = video_1['_deposit']['pid']['value']
    with app.test_request_context():
        url_no_existing_exporter = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='blabla')
        url_not_valid_type_record = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='smil')
        url_valid_smil = url_for(
            'invenio_records_ui.recid_export', pid_value=vid, format='smil')
        url_valid_json = url_for(
            'invenio_records_ui.recid_export', pid_value=pid, format='json')

    with app.test_client() as client:
        # Test that default view function can deal with multiple parameters.
        res = client.get(url_no_existing_exporter)
        assert res.status_code == 404
        res = client.get(url_not_valid_type_record)
        assert res.status_code == 400
        res = client.get(url_valid_smil)
        assert res.status_code == 200
        res = client.get(url_valid_json)
        assert res.status_code == 200
        # Test that actual data has been exported (not blank)
        data_start = res.data.find(b'<pre>') + 5
        data_end = res.data.find(b'</pre>', data_start)
        data = res.data[data_start:data_end]
        assert len(data) > 1
