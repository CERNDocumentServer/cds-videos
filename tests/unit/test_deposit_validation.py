# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
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

"""Test deposit validation."""

from __future__ import absolute_import, print_function

import json
import pytest

from flask import current_app

from cds.modules.deposit.loaders import partial_project_loader, \
    partial_video_loader, project_loader, video_loader
from cds.modules.deposit.loaders.loader import MarshmallowErrors


@pytest.mark.parametrize('remove_key, loader', [
    (key, loader)
    for key in ['date', 'title.title']
    for loader in [project_loader, video_loader]
])
def test_missing_fields(
        es, location, project_deposit_metadata, remove_key, loader):
    """Test project deposit validation errors due to missing fields."""
    # Remove key in path
    key_path = remove_key.split('.')
    project_deposit_metadata['_deposit'] = {'id': '123456'}
    sub = project_deposit_metadata
    for k in key_path[:-1]:
        sub = sub[k]
    del sub[key_path[-1]]
    # Check marshmallow errors
    with current_app.test_request_context(
        '/api/deposits/project',
            method='PUT',
            data=json.dumps(project_deposit_metadata),
            content_type='application/json'):
            with pytest.raises(MarshmallowErrors) as errors:
                loader()
            assert '400 Bad Request' in str(errors.value)
            error_body = json.loads(errors.value.get_body())
            assert error_body['status'] == 400
            assert error_body['errors'][0]['field'] == remove_key


@pytest.mark.parametrize('add_key, loader', [
    (key, loader)
    for key in ['invalid', 'title.id', 'description.id']
    for loader in [project_loader, video_loader,
                   partial_project_loader, partial_video_loader]
])
def test_unknown_fields(
        es, location, project_deposit_metadata, add_key, loader):
    """Test validation error due to unknown fields."""
    # Add key in path
    key_path = add_key.split('.')
    project_deposit_metadata['_deposit'] = {'id': '123456'}
    sub = project_deposit_metadata
    for k in key_path[:-1]:
        sub = sub[k]
    sub[key_path[-1]] = ''
    with current_app.test_request_context(
        '/api/deposits/video',
            method='PUT',
            data=json.dumps(project_deposit_metadata),
            content_type='application/json'):
        with pytest.raises(MarshmallowErrors) as errors:
            video_loader()
        assert '400 Bad Request' in str(errors.value)

        error_body = json.loads(errors.value.get_body())
        assert error_body['status'] == 400
        assert error_body['errors'][0]['field'] == add_key
