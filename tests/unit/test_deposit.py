# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017 CERN.
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

"""Test deposit."""

from __future__ import absolute_import, print_function

import json

from cds.modules.deposit.api import CDSDeposit, Project
from cds.modules.deposit.views import to_links_js
from flask import current_app, request, url_for
from flask_principal import RoleNeed, identity_loaded
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from invenio_files_rest.models import FileInstance, ObjectVersionTag, Bucket
from invenio_files_rest.models import ObjectVersion


def test_deposit_link_factory_has_bucket(
        app, db, es, users, location, cds_jsonresolver, deposit_rest,
        json_headers, json_partial_project_headers, json_partial_video_headers,
        video_deposit_metadata, project_deposit_metadata):
    """Test bucket link factory retrieval of a bucket."""
    with app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)

        # Test links for project
        res = client.post(
            url_for('invenio_deposit_rest.project_list'),
            data=json.dumps(project_deposit_metadata),
            headers=json_partial_project_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        links = data['links']
        pid = data['metadata']['_deposit']['id']
        assert 'bucket' in links
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid)

        # Test links for videos
        res = client.post(
            url_for('invenio_deposit_rest.video_list'),
            data=json.dumps({
                '_project_id': pid,
            }), headers=json_partial_video_headers)
        assert res.status_code == 201
        data = json.loads(res.data.decode('utf-8'))
        links = data['links']
        pid = data['metadata']['_deposit']['id']
        assert 'bucket' in links
        assert links['html'] == current_app.config['DEPOSIT_UI_ENDPOINT']\
            .format(
                host=request.host,
                scheme=request.scheme,
                pid_value=pid)


def test_links_filter(es, location, deposit_metadata):
    """Test Jinja to_links_js filter."""
    assert to_links_js(None) == []
    deposit = Project.create(deposit_metadata)
    links = to_links_js(deposit.pid, deposit)
    assert all([key in links for key in ['self', 'edit', 'publish', 'bucket',
               'files', 'html', 'discard']])
    self_url = links['self']
    assert links['discard'] == self_url + '/actions/discard'
    assert links['edit'] == self_url + '/actions/edit'
    assert links['publish'] == self_url + '/actions/publish'
    assert links['files'] == self_url + '/files'
    links_type = to_links_js(deposit.pid, deposit, 'project')
    self_url_type = links_type['self']
    assert links_type['discard'] == self_url_type + '/actions/discard'
    assert links_type['edit'] == self_url_type + '/actions/edit'
    assert links_type['publish'] == self_url_type + '/actions/publish'
    assert links_type['files'] == self_url_type + '/files'
    with current_app.test_client() as client:
        data = client.get(links_type['html']).get_data().decode('utf-8')
        for key in links_type:
            assert links_type[key] in data


def test_publish_process_files(app, db, location):
    """Test _process_files changing master tags on bucket snapshots."""
    deposit = CDSDeposit.create(dict(date='1/2/3', category='cat', type='type',
                                title=dict(title='title'),
                                report_number=dict(report_number='1234'),
                                videos=[]))
    # deposit has no files, so _process_files must yield None
    with deposit._process_files(None, dict()) as data:
        assert data is None
    bucket = deposit.files.bucket
    master_obj = ObjectVersion.create(
        bucket=bucket,
        key='master',
        _file_id=FileInstance.create())
    number_of_slaves = 10
    for i in range(number_of_slaves):
        slave_obj = ObjectVersion.create(
            bucket=bucket,
            key='slave{}.mp4'.format(i + 1),
            _file_id=FileInstance.create())
        ObjectVersionTag.create(slave_obj, 'master', master_obj.version_id)
        ObjectVersionTag.create(slave_obj, 'media_type', 'video')
        ObjectVersionTag.create(slave_obj, 'context_type', 'subformat')
    assert Bucket.query.count() == 1
    with deposit._process_files(None, dict()):
        # the snapshot bucket must have been created
        assert Bucket.query.count() == 2
        for bucket in Bucket.query.all():
            master_version = [str(obj.version_id) for obj in bucket.objects
                              if 'master' not in obj.get_tags()][0]
            # the master of each slave must be in the same bucket
            for obj in bucket.objects:
                if str(obj.version_id) != master_version:
                    assert obj.get_tags()['master'] == master_version
                    assert obj.get_tags()['media_type'] == 'video'
                    assert obj.get_tags()['context_type'] == 'subformat'


def test_deposit_access_rights_based_on_user_id(api_app, users, cds_depid,
                                                deposit_rest):
    """Test deposit access rights based on user ID.

    Tests that a user can't access a deposit created by a different user.
    """
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        # User is the creator of the deposit, so everything is fine
        assert client.get(deposit_url).status_code == 200

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        # User shouldn't have access to this deposit
        assert client.get(deposit_url).status_code == 403


def test_deposit_access_rights_based_on_egroup(api_app, users, cds_depid,
                                               deposit_rest):
    """Test deposit access rights based on the e-groups.

    Tests that a user can access a deposit based on the e-group permissions.
    """
    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Add additional group to the user."""
        identity.provides |= set([RoleNeed('test-egroup@cern.ch')])

    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        deposit_url = url_for('invenio_deposit_rest.project_item',
                              pid_value=cds_depid)
        assert client.get(deposit_url).status_code == 200
