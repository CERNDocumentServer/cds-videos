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
                                     video_resolver, deposit_build_url,
                                     is_deposit, record_unbuild_url)
from invenio_pidstore.providers.recordid import RecordIdProvider
from cds.modules.deposit.errors import DiscardConflict


def test_is_deposit():
    """Test is deposit function."""
    assert is_deposit('/deposit/1') is True
    assert is_deposit('/record/1') is False


def test_record_unbuild_url():
    """Test record unbuild url."""
    assert '1' == record_unbuild_url('/deposit/1')
    assert '1' == record_unbuild_url('/record/1')


def test_record_build_url():
    """Test record build url."""
    assert '/record/1' == record_build_url(1)


def test_deposit_build_url():
    """Test deposit build url."""
    assert '/deposit/1' == deposit_build_url(1)
    assert '/deposit/1' == deposit_build_url('1')
    assert '/deposit/95b0716a-c726-4481-96fe-2aa02c72cd41' == \
        deposit_build_url(uuid.UUID('95b0716a-c726-4481-96fe-2aa02c72cd41'))


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
    with app.test_request_context():
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
    # publish project
    with app.test_request_context():
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
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/project-v1.0.0.json'),
        '_access': {'read': 'open'},
        'videos': [],
    }

    project_video_1 = {
        'title': {
            'title': 'video 1',
        },
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/video-v1.0.0.json'),
        '_access': {'read': 'open'},
    }

    with app.test_request_context():
        login_user(users[0])

        # create empty project
        project = Project.create(project_data).commit()
        # create video
        video_1 = Video.create(project_video_1)

        # check project <--/--> video
        assert project['videos'] == []
        assert video_1.project is None

        # add videos inside the project
        video_1.project = project

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
    #  project = project.commit()

    # try to fail because a video added
    project = project.edit()
    project_video = {
        'title': {
            'title': 'video 1',
        },
        '$schema': ('https://cdslabs.cern.ch/schemas/'
                    'deposits/records/video-v1.0.0.json'),
        '_access': {'read': 'open'},
    }
    video = Video.create(project_video)
    video.project = project
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

    with app.test_request_context():
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
        assert videos[0]['title']['title'] == 'Video 1'
        assert videos[1]['title']['title'] == 'Video 2'
