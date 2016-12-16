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
import uuid

from flask_security import login_user
from cds.modules.deposit.api import (record_build_url, Project, Video,
                                     video_resolver, video_build_url,
                                     is_deposit, record_unbuild_url)
from invenio_accounts.models import User
from invenio_pidstore.providers.recordid import RecordIdProvider
from invenio_pidstore.errors import PIDInvalidAction
from cds.modules.deposit.errors import DiscardConflict
from invenio_records.models import RecordMetadata


def test_is_deposit():
    """Test is deposit function."""
    assert is_deposit('/api/deposit/1') is True
    assert is_deposit('/record/1') is False


def test_record_unbuild_url(deposit_rest):
    """Test record unbuild url."""
    assert '1' == record_unbuild_url('/deposits/video/1')
    assert '1' == record_unbuild_url('/record/1')


def test_record_build_url(deposit_rest):
    """Test record build url."""
    assert '/record/1' == record_build_url(1)


def test_video_build_url(deposit_rest):
    """Test deposit build url."""
    assert '/deposits/video/1' == video_build_url(1)
    assert '/deposits/video/1' == video_build_url('1')
    assert '/deposits/video/95b0716a-c726-4481-96fe-2aa02c72cd41' == \
        video_build_url(uuid.UUID('95b0716a-c726-4481-96fe-2aa02c72cd41'))


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_publish_all_videos(app, project):
    """Test video publish."""
    (project, video_1, video_2) = project

    # check video1 is not published
    assert video_1['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # publish project
    new_project = project.publish()
    # check project and all video are published
    assert new_project['_deposit']['status'] == 'published'
    videos = video_resolver(new_project.video_ids)
    assert len(videos) == 2
    for video in videos:
        assert video['_deposit']['status'] == 'published'


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_publish_one_video(app, project):
    """Test video publish."""
    (project, video_1, video_2) = project

    # check video1 is not published
    assert video_1['_deposit']['status'] == 'draft'
    assert video_2['_deposit']['status'] == 'draft'
    assert project['_deposit']['status'] == 'draft'
    # [publish project]
    # publish one video
    video_1 = video_1.publish()
    project = video_1.project
    # publish the project (with one video still not publish)
    project = project.publish()
    # check project and all video are published
    assert project['_deposit']['status'] == 'published'
    videos = video_resolver(project.video_ids)
    assert len(videos) == 2
    for video in videos:
        assert video['_deposit']['status'] == 'published'


def test_find_refs(project):
    """Test find refs."""
    (project, video_1, video_2) = project
    assert project._find_refs([video_1.ref]) == {0: video_1.ref}
    assert project._find_refs([video_2.ref]) == {1: video_2.ref}
    assert project._find_refs([video_1.ref, video_2.ref]) == \
        {0: video_1.ref, 1: video_2.ref}
    assert project._find_refs(['not-found']) == {}


def test_update_videos(project):
    """Test update videos."""
    (project, video_1, video_2) = project
    new_ref_2 = '/deposit/456'
    project._update_videos([video_2.ref], [new_ref_2])
    assert project['videos'] == [
        {'$reference': video_1.ref}, {'$reference': new_ref_2}]
    project._update_videos(['not-found'], ['ref-not-found'])
    assert project['videos'] == [
        {'$reference': video_1.ref}, {'$reference': new_ref_2}]


def test_delete_videos(project):
    """Test update videos."""
    (project, video_1, video_2) = project
    project._delete_videos([video_2.ref])
    assert project['videos'] == [{'$reference': video_1.ref}]
    project._delete_videos(['not-found'])
    assert project['videos'] == [{'$reference': video_1.ref}]


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_add_video(app, es, cds_jsonresolver, users, location):
    """Test add video."""
    project_data = {
        'title': {
            'title': 'my project',
        },
        'videos': [],
    }

    login_user(User.query.get(users[0]))

    # create empty project
    project = Project.create(project_data).commit()

    # check project <--/--> video
    assert project['videos'] == []

    # create video
    project_video_1 = {
        'title': {
            'title': 'video 1',
        },
        '_project_id': project['_deposit']['id'],
    }
    video_1 = Video.create(project_video_1)

    # check project <----> video
    assert project._find_refs([video_1.ref])
    assert video_1.project.id == project.id


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_project_discard(app, project_published):
    """Test project discard."""
    (project, video_1, video_2) = project_published

    # try successfully to discard a project
    original_title = project['title']['title']
    new_title = 'modified project'
    project = project.edit()
    project['title']['title'] = 'modified project'
    assert project['title']['title'] == new_title
    project = project.discard()
    assert project['title']['title'] == original_title

    # try to fail because a video added
    project = project.edit()
    project_video = {
        'title': {
            'title': 'video 1',
        },
        '_project_id': project['_deposit']['id'],
    }
    Video.create(project_video)
    with pytest.raises(DiscardConflict):
        project.discard()


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
def test_project_edit(app, project_published):
    """Test project edit."""
    (project, video_1, video_2) = project_published
    assert project.status == 'published'
    assert video_1.status == 'published'
    assert video_2.status == 'published'

    # Edit project (change project title)
    new_project = project.edit()
    assert new_project.status == 'draft'
    new_project.update(title={'title': 'My project'})

    # Edit videos inside project (change video titles)
    videos = video_resolver(new_project.video_ids)
    assert len(videos) == 2
    for i, video in enumerate(videos):
        assert video.status == 'published'
        new_video = video.edit()
        assert new_video.status == 'draft'
        new_video.update(title={'title': 'Video {}'.format(i + 1)})
        new_video.publish()

    # Publish all changes
    new_project.publish()

    # Check that everything is published
    videos = video_resolver(new_project.video_ids)
    assert new_project.status == 'published'
    assert all(video.status == 'published' for video in videos)

    # Check that all titles where properly changed
    assert new_project['title']['title'] == 'My project'
    assert videos[0]['title']['title'] in ['Video 1', 'Video 2']
    assert videos[1]['title']['title'] in ['Video 1', 'Video 2']
    assert videos[0]['title']['title'] != videos[1]['title']['title']


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False, True])
def test_project_delete_not_published(app, project, force):
    """Test project delete when all is not published."""
    (project, video_1, video_2) = project

    project_id = project.id
    video_1_id = video_1.id
    video_2_id = video_2.id

    assert project.status == 'draft'
    assert video_1.status == 'draft'
    assert video_2.status == 'draft'

    project = project.delete(force=force)

    reclist = RecordMetadata.query.filter(RecordMetadata.id.in_(
        [project_id, video_1_id, video_2_id])).all()

    if force:
        assert len(reclist) == 0
    else:
        assert len(reclist) == 3
        for rec in reclist:
            assert rec.json is None


@mock.patch('cds.modules.records.providers.CDSRecordIdProvider.create',
            RecordIdProvider.create)
@pytest.mark.parametrize('force', [False])  # , True])
def test_project_delete_one_video_published(app, project, force):
    """Test project delete when one video is published."""
    def check_project(number_of_videos, video_2_status, video_1_ref,
                      video_2_ref, project_id):
        video_1_meta = RecordMetadata.query.filter_by(id=video_1_id).first()
        video_2_meta = RecordMetadata.query.filter_by(id=video_2_id).first()
        project_meta = RecordMetadata.query.filter_by(id=project_id).first()

        assert video_1_meta.json is not None
        assert video_2_meta.json is not None

        assert {'$reference': video_1_ref} in project_meta.json['videos']
        assert {'$reference': video_2_ref} in project_meta.json['videos']
        assert len(project_meta.json['videos']) == number_of_videos

        assert project.status == 'draft'
        assert video_1.status == 'draft'
        assert video_2.status == video_2_status

    (project, video_1, video_2) = project

    # publish video_2
    video_2 = video_2.publish()

    project_id = project.id
    video_1_id = video_1.id
    video_2_id = video_2.id

    video_1_ref = video_1.ref
    video_2_ref = video_2.ref

    assert project.status == 'draft'
    assert video_1.status == 'draft'
    assert video_2.status == 'published'

    # you can't delete because there is a video published!
    with pytest.raises(PIDInvalidAction):
        project.delete(force=force)

    check_project(2, 'published', video_1_ref, video_2_ref, project_id)

    # edit video_2
    video_2 = video_2.edit()
    video_2_id = video_2.id
    project_id = video_2.project.id
    video_1_ref = video_1.ref
    video_2_ref = video_2.ref

    # you can't delete because video_2 was previously published
    with pytest.raises(PIDInvalidAction):
        project.delete(force=force)

    check_project(2, 'draft', video_1_ref, video_2_ref, project_id)

    # discard video_2
    video_2 = video_2.discard()
    video_2_id = video_2.id
    project_id = video_2.project.id
    video_2_ref = video_2.ref

    # you can't delete because there is a video published!
    with pytest.raises(PIDInvalidAction):
        project.delete(force=force)

    check_project(2, 'published', video_1_ref, video_2_ref, project_id)

    # TODO delete video_2
    #  video_2.delete(force=force)
    #  project_id = video_1.project.id

    #  project.delete(force=force)


def test_inheritance(app, project):
    """Test that videos inherit the proper fields from parent project."""
    (project, video, _) = project
    assert 'category' in project
    assert 'type' in project

    # Publish the video
    video = video.publish()
    assert 'category' in video
    assert 'type' in video
    assert video['category'] == project['category']
    assert video['type'] == project['type']
