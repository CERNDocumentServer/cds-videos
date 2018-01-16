# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017, 2017 CERN.
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

"""Test CDS report number generation."""

from __future__ import absolute_import, print_function

from flask_security import login_user
from invenio_accounts.models import User
from cds.modules.deposit.api import \
    Project, deposit_videos_resolver, record_video_resolver, \
    record_project_resolver

from helpers import prepare_videos_for_publish


def video_resolver_sorted(ids):
    """Return videos with ascending RN order."""
    return sorted(deposit_videos_resolver(ids), key=lambda x: x.report_number)


def record_video_resolver_sorted(ids):
    """Return videos with ascending RN order."""
    return sorted([record_video_resolver(id_) for id_ in ids],
                  key=lambda x: x.report_number)


def check_deposit(dep, expected_rn):
    """Check that a deposit has properly generated its report number."""
    assert 'recid' in dep
    assert dep.report_number == expected_rn
    stored = record_project_resolver(str(dep['recid'])) \
        if isinstance(dep, Project) \
        else record_video_resolver(str(dep['recid']))
    assert stored.report_number == expected_rn


def test_one_video(db, api_project, users, current_year):
    """Test one video."""
    login_user(User.query.get(users[0]))
    project, video_1, video_2 = api_project
    prepare_videos_for_publish([video_1, video_2])
    check_deposit(video_1.publish(), 'CERN-MOVIE-{0}-1-1'.format(current_year))


def test_only_videos(db, api_project, users, current_year):
    """Test only videos."""
    login_user(User.query.get(users[0]))
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    for i, video in enumerate([video_1, video_2]):
        video = video.publish()
        check_deposit(video, 'CERN-MOVIE-{0}-1-{1}'.format(current_year, i + 1))


def test_only_project(db, api_project, users, current_year):
    """Test only project."""
    login_user(User.query.get(users[0]))
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    check_deposit(project.publish(), 'CERN-MOVIE-{0}-1'.format(current_year))


def test_project_and_videos(db, api_project, users, current_year):
    """Test project and video."""
    login_user(User.query.get(users[0]))
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    project = project.publish()
    check_deposit(project, 'CERN-MOVIE-{0}-1'.format(current_year))
    for i, video in enumerate(record_video_resolver_sorted(project.video_ids)):
        check_deposit(video, 'CERN-MOVIE-{0}-1-{1}'.format(current_year, i + 1))


def test_video_then_project(db, api_project, users, current_year):
    """Test video and then project."""
    login_user(User.query.get(users[0]))
    (project, video_1, video_2) = api_project
    prepare_videos_for_publish([video_1, video_2])
    video_1 = video_1.publish()
    check_deposit(video_1, 'CERN-MOVIE-{0}-1-1'.format(current_year))

    project = video_1.project
    project = project.publish()
    check_deposit(project, 'CERN-MOVIE-{0}-1'.format(current_year))

    video_2 = record_video_resolver_sorted(project.video_ids)[1]
    check_deposit(video_2, 'CERN-MOVIE-{0}-1-2'.format(current_year))
