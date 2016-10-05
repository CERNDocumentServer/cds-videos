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
from flask import current_app, g, request, url_for
from flask_login import login_user
from flask_principal import Identity
from invenio_accounts.models import User
from invenio_db import db
from invenio_files_rest.models import Bucket
from invenio_records.models import RecordMetadata
from invenio_records_files.api import RecordsBuckets

from cds.modules.deposit.api import CDSDeposit
from cds.modules.deposit.links import deposit_links_factory
from cds.modules.deposit.permissions import can_edit_deposit
from cds.modules.deposit.views import to_links_js


def test_deposit_link_factory_has_bucket(app, db, location):
    """Test bucket link factory retrieval of a bucket."""
    bucket = Bucket.create()
    with app.test_request_context(),\
        mock.patch('invenio_deposit.links.deposit_links_factory',
                   return_value={}):

        with db.session.begin_nested():
            record = RecordMetadata()
            RecordsBuckets.create(record, bucket)
            db.session.add(record)
        pid = mock.Mock()
        pid.get_assigned_object.return_value = record.id
        links = deposit_links_factory(pid)
        assert links['bucket'] == url_for(
            'invenio_files_rest.bucket_api', bucket_id=bucket.id,
            _external=True)
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid.pid_value,
        )


def test_cds_deposit(location):
    """Test CDS deposit creation."""
    deposit = CDSDeposit.create({})
    assert '_buckets' in deposit


def test_links_filter(location):
    """Test Jinja to_links_js filter."""
    assert to_links_js(None) == []
    deposit = CDSDeposit.create({})
    links = to_links_js(deposit.pid, deposit)
    assert all([key in links for key in ['self', 'edit', 'publish', 'bucket',
               'files', 'html', 'discard']])
    self_url = links['self']
    assert links['discard'] == self_url + '/actions/discard'
    assert links['edit'] == self_url + '/actions/edit'
    assert links['publish'] == self_url + '/actions/publish'
    assert links['files'] == self_url + '/files'


def test_permissions(location):
    """Test deposit permissions."""
    deposit = CDSDeposit.create({})
    deposit.commit()
    user = User(email='user@cds.cern', password='123456', active=True)
    g.identity = Identity(user.id)
    db.session.add(user)
    db.session.commit()
    login_user(user, force=True)
    assert not can_edit_deposit(deposit)
    deposit['_deposit']['owners'].append(user.id)
    assert can_edit_deposit(deposit)
