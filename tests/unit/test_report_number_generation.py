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

"""Test CDS report number generation."""

from __future__ import absolute_import, print_function

from cds.modules.deposit.api import video_resolver, project_resolver, Project


def video_resolver_sorted(ids):
    """Return videos with ascending RN order."""
    return sorted(video_resolver(ids), key=lambda x: x.report_number)


def check_deposit(dep, expected_rn):
    """Check that a deposit has properly generated its report number."""
    assert 'recid' in dep
    stored = project_resolver(str(dep['recid'])) \
        if isinstance(dep, Project) else video_resolver([str(dep['recid'])])[0]
    for rec in [dep, stored]:
        assert rec.report_number
        assert rec.report_number == expected_rn


def test_one_video(app, db, project):
    """Test one video."""
    check_deposit(project[1].publish(), 'CERN-MOVIE-2016-1-1'.format())


def test_only_videos(app, db, project):
    """Test only videos."""
    (project, video_1, video_2) = project
    for i, video in enumerate([video_1, video_2]):
        video = video.publish()
        check_deposit(video, 'CERN-MOVIE-2016-1-{}'.format(i + 1))


def test_only_project(app, db, project):
    """Test only project."""
    check_deposit(project[0].publish(), 'CERN-MOVIE-2016-1')


def test_project_and_videos(app, db, project):
    """Test project and video."""
    (project, video_1, video_2) = project
    project = project.publish()
    check_deposit(project, 'CERN-MOVIE-2016-1')
    for i, video in enumerate(video_resolver_sorted(project.video_ids)):
        check_deposit(video, 'CERN-MOVIE-2016-1-{}'.format(i + 1))


def test_video_then_project(app, db, project):
    """Test video and then project."""
    (project, video_1, video_2) = project
    video_1 = video_1.publish()
    check_deposit(video_1, 'CERN-MOVIE-2016-1-1')

    project = video_1.project
    project = project.publish()
    check_deposit(project, 'CERN-MOVIE-2016-1')

    video_2 = video_resolver_sorted(project.video_ids)[1]
    check_deposit(video_2, 'CERN-MOVIE-2016-1-2')
