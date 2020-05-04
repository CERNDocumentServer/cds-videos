# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2018, 2020 CERN.
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

"""Test cds maintenance."""

from __future__ import absolute_import, print_function

import pytest

from cds.modules.maintenance.subformats import (
    create_all_missing_subformats,
    create_all_subformats,
    create_subformat,
)
from mock import patch


def _fill_video_subformats(qualities):
    return [dict(tags=dict(preset_quality=q)) for q in qualities]


@patch('cds.modules.maintenance.subformats.get_all_distinct_qualities')
def test_subformats_input_validation(sorenson_all_qualities):
    """Test subformats module inputs."""
    with pytest.raises(Exception):
        create_all_missing_subformats('otherid', 'value')
        create_subformat('otherid', 'value', '')
        create_all_subformats('otherid', 'value')

        create_subformat('recid', 'value', None)
        sorenson_all_qualities.return_value = ['240p', '360p', '480p']
        create_subformat('recid', 'value', '720p')


@patch('cds.modules.maintenance.subformats._schedule')
@patch('cds.modules.records.api.CDSVideosFilesIterator.get_video_subformats')
@patch('cds.modules.maintenance.subformats.can_be_transcoded')
@patch('cds.modules.maintenance.subformats.get_all_distinct_qualities')
@patch('cds.modules.maintenance.subformats._get_master_video')
@patch('cds.modules.maintenance.subformats._resolve_deposit')
def test_create_all_missing_subformats(
    resolve_deposit,
    get_master_video,
    sorenson_all_qualities,
    sorenson_can_transcode,
    video_subformats,
    schedule,
):
    """Test method to create missing subformats."""
    # set up
    schedule.return_value = 'valid-uuid'
    resolve_deposit.return_value = None, 'dep_uuid'
    get_master_video.return_value = (
        dict(version_id='uuid_version'),
        '16:9',
        '',
        '',
    )

    # test no missing subformats
    video_subformats.return_value = _fill_video_subformats(
        ['240p', '360p', '480p']
    )
    sorenson_all_qualities.return_value = ['240p', '360p', '480p']
    sorenson_can_transcode.return_value = True
    sorenson_can_transcode.side_effect = None
    result, _ = create_all_missing_subformats('recid', 2)
    assert not result

    # test 480p missing, 720p not valid
    video_subformats.return_value = _fill_video_subformats(['240p', '360p'])
    sorenson_all_qualities.return_value = ['240p', '360p', '480p', '720p']

    def all_but_highest(q, ar, w, h):
        return q != '720p'

    sorenson_can_transcode.side_effect = all_but_highest
    result, _ = create_all_missing_subformats('recid', 2)
    assert result == ['480p']

    # test all missing
    video_subformats.return_value = []
    sorenson_all_qualities.return_value = ['240p', '360p', '480p', '720p']
    sorenson_can_transcode.return_value = True
    sorenson_can_transcode.side_effect = None
    result, _ = create_all_missing_subformats('recid', 2)
    assert sorted(result) == sorted(['240p', '360p', '480p', '720p'])


@patch('cds.modules.maintenance.subformats.MaintenanceTranscodeVideoTask')
@patch('cds.modules.maintenance.subformats._schedule')
@patch('cds.modules.maintenance.subformats.can_be_transcoded')
@patch('cds.modules.maintenance.subformats.get_all_distinct_qualities')
@patch('cds.modules.maintenance.subformats._get_master_video')
@patch('cds.modules.maintenance.subformats._resolve_deposit')
def test_create_subformat(
    resolve_deposit,
    get_master_video,
    sorenson_all_qualities,
    sorenson_can_transcode,
    schedule,
    _,
):
    """Test method to recreate a specific subformat quality."""
    # set up
    schedule.return_value = 'valid-uuid'
    resolve_deposit.return_value = None, 'dep_uuid'
    get_master_video.return_value = (
        dict(version_id='uuid_version'),
        '16:9',
        '',
        '',
    )
    sorenson_all_qualities.return_value = [
        '240p',
        '360p',
        '480p',
        '720p',
        '1080p',
    ]

    # test valid quality
    sorenson_can_transcode.return_value = dict(quality='360p')
    sorenson_can_transcode.side_effect = None
    result, _ = create_subformat('recid', 'value', '360p')
    assert result == dict(quality='360p')

    # test not valid quality
    def all_but_highest(q, ar, w, h):
        return q != '720p'

    sorenson_can_transcode.side_effect = all_but_highest
    result, _ = create_subformat('recid', 'value', '720p')
    assert not result


@patch('cds.modules.maintenance.subformats._schedule')
@patch('cds.modules.maintenance.subformats.can_be_transcoded')
@patch('cds.modules.maintenance.subformats.get_all_distinct_qualities')
@patch('cds.modules.maintenance.subformats._get_master_video')
@patch('cds.modules.maintenance.subformats._resolve_deposit')
def test_recreate_all_subformats(
    resolve_deposit,
    get_master_video,
    sorenson_all_qualities,
    sorenson_can_transcode,
    schedule,
):
    """Test method to create missing subformats."""
    # set up
    schedule.return_value = 'valid-uuid'
    resolve_deposit.return_value = None, 'dep_uuid'
    get_master_video.return_value = (
        dict(version_id='uuid_version'),
        '16:9',
        '',
        '',
    )
    sorenson_all_qualities.return_value = [
        '240p',
        '360p',
        '480p',
        '720p',
        '1080p',
    ]

    # test no subformats possible, should never happen
    sorenson_can_transcode.return_value = False
    result, _ = create_all_subformats('recid', 2)
    assert not result

    # test recreate subformat but highest
    def all_but_highest(q, ar, w, h):
        return q != '1080p'

    sorenson_can_transcode.side_effect = all_but_highest
    result, _ = create_all_subformats('recid', 2)
    assert sorted(result) == sorted(['240p', '360p', '480p', '720p'])

    # test recreate all subformats
    sorenson_can_transcode.return_value = True
    sorenson_can_transcode.side_effect = None
    result, _ = create_all_subformats('recid', 2)
    assert sorted(result) == sorted(['240p', '360p', '480p', '720p', '1080p'])
