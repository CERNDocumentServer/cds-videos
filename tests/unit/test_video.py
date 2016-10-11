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
import pytest

from cds.modules.deposit.api import (record_build_url,
                                     video_resolver, deposit_build_url,
                                     Video)
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_pidstore.errors import PIDInvalidAction
from invenio_records.models import RecordMetadata


def test_video_resolver(app, project):
    """Test vide resolver."""
    (project, video_1, video_2) = project
    videos = video_resolver(
        [video_1['_deposit']['id'], video_2['_deposit']['id']])
    original = [video_1.id, video_2.id]
    original.sort()
    resolved = [videos[0].id, videos[1].id]
    resolved.sort()
    assert original == resolved


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_video_publish_and_edit(app, project):
    """Test video publish and edit."""
    (project, video_1, video_2) = project
    video_path_1 = project['videos'][0]['$reference']
    video_path_2 = project['videos'][1]['$reference']

    deposit_project_schema = ('https://cdslabs.cern.ch/schemas/'
                              'deposits/records/project-v1.0.0.json')
    deposit_video_schema = ('https://cdslabs.cern.ch/schemas/'
                            'deposits/records/video-v1.0.0.json')
    record_video_schema = ('https://cdslabs.cern.ch/schemas/'
                           'records/video-v1.0.0.json')

    # check video1 is not published
    assert video_1['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # and the schema is a deposit
    assert video_1['$schema'] == deposit_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema

    # update video

    # [publish the video 1]
    video_1 = video_1.publish()

    project = video_1.project
    (_, record_video_1) = video_1.fetch_published()
    record_video_id_1 = record_video_1['recid']
    record_path_1 = record_build_url(record_video_id_1)

    # check new link project -> video
    assert video_1['_deposit']['status'] == 'published'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # check the schema is a record
    assert record_video_1['$schema'] == record_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema
    # check video recid is inside the list
    assert any(video_ref['$reference'] == record_path_1
               for video_ref in project['videos']) is True
    # and there is not the old id (when the video was a deposit)
    assert any(video_ref['$reference'] == video_path_1
               for video_ref in project['videos']) is False
    # and still exists video 2 deposit id
    assert any(video_ref['$reference'] == video_path_2
               for video_ref in project['videos']) is True

    # [edit the video 1]
    video_1_v2 = Video.create(record_video_1)
    video_1_v2 = video_1_v2.edit()

    # check video1 is not published
    assert video_1_v2['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # check the schema is a record
    assert video_1_v2['$schema'] == deposit_video_schema
    assert video_2['$schema'] == deposit_video_schema
    assert project['$schema'] == deposit_project_schema
    # check video1 v1 recid is NOT inside the list
    assert any(video_ref['$reference'] == record_path_1
               for video_ref in project['videos']) is False
    # check video1 v2 is inside the list
    video_path_1_v2 = deposit_build_url(video_1_v2['_deposit']['id'])
    assert any(video_ref['$reference'] == video_path_1_v2
               for video_ref in project['videos']) is True


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False, True])
def test_delete_video_not_published(app, project, force):
    """Test video delete when draft."""
    (project, video_1, video_2) = project

    project_id = project.id
    video_1_ref = video_1.ref
    video_2_id = video_2.id

    assert project.status == 'draft'
    assert video_2.status == 'draft'

    video_2.delete(force=force)

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert [{'$reference': video_1_ref}] == project_meta.json['videos']

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    if force:
        video_2_meta is None
    else:
        assert video_2_meta.json is None


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False, True])
def test_delete_video_published(app, project, force):
    """Test video delete after published."""
    (project, video_1, video_2) = project

    video_2 = video_2.publish()

    project_id = project.id
    video_2_id = video_2.id
    video_2_ref = video_2.ref

    assert project.status == 'draft'
    assert video_2.status == 'published'

    with pytest.raises(PIDInvalidAction):
        video_2.delete(force=force)

    video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
    assert video_2_meta.json is not None

    project_meta = RecordMetadata.query.filter_by(id=project_id).first()
    assert {'$reference': video_2_ref} in project_meta.json['videos']
