# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017, 2018 CERN.
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

"""Test serializers."""

from __future__ import absolute_import, print_function

import xml.etree.ElementTree as ET

from cds.modules.deposit.api import Video
from cds.modules.records.serializers.drupal import VideoDrupal
from cds.modules.records.serializers.smil import Smil
from cds.modules.records.serializers.vtt import VTT


def test_smil_serializer(video_record_metadata):
    """Test smil serializer."""
    rec = video_record_metadata

    def parse_and_test(rec, subformats_num, first_playlist_quality):
        serializer = Smil(record=rec)
        data = serializer.format()
        root = ET.fromstring(data)
        assert root.tag == 'smil'
        assert len(root[1][0]) == subformats_num
        for child in root[1][0]:
            assert child.tag == 'video'
            assert 'system-bitrate' in child.attrib
            assert 'width' in child.attrib
            assert 'height' in child.attrib
            assert 'src' in child.attrib
        # check if the first files has the first playlist quality
        # of 720 / 480 / 240 after deleting the subformats one by one
        assert root[1][0][0].get('height') == first_playlist_quality

    parse_and_test(rec, 4, '720')

    # remove the file that has the first playlist quality of 720
    rec['_files'][0]['subformat'] = list(
        filter(
            lambda subformat: subformat['tags']['height'] != '720',
            rec['_files'][0]['subformat']
        )
    )
    parse_and_test(rec, 3, '480')

    # remove the file that has the first playlist quality of 480
    rec['_files'][0]['subformat'] = list(
        filter(
            lambda subformat: subformat['tags']['height'] != '480',
            rec['_files'][0]['subformat']
        )
    )
    parse_and_test(rec, 2, '240')


def test_vtt_serializer(video_record_metadata):
    """Test vtt serializer."""
    serializer = VTT(record=video_record_metadata)
    data = serializer._format_frames(video_record_metadata)
    start_times, end_times = [[info[key] for info in data]
                              for key in ['start_time', 'end_time']]

    # Check first and last timestamp
    assert start_times[0] == '00:00.000'
    assert end_times[-1] == VTT.time_format(
        float(video_record_metadata['_files'][0]['tags']['duration']))

    # Check that timestamps are ascending
    assert all([sorted(l) == l for l in [start_times, end_times]])

    # Check that there are no time gaps between frames
    assert start_times[1:] == end_times[:-1]


def test_drupal_serializer(video_record_metadata, deposit_metadata):
    """Test drupal serializer."""
    duration = '00:01:00.140'
    report_number = 'RN-01'
    video_record_metadata.update(deposit_metadata)
    video_record_metadata.update({
        'report_number': [report_number],
        '$schema': Video.get_record_schema(),
        'duration': duration,
        'contributors': [
            {'name': 'paperone', 'role': 'Director'},
            {'name': 'topolino', 'role': 'Music by'},
            {'name': 'nonna papera', 'role': 'Producer'},
            {'name': 'pluto', 'role': 'Director'},
            {'name': 'zio paperino', 'role': 'Producer'}
        ],
    })
    expected = dict(
        caption_en='in tempor reprehenderit enim eiusmod <b><i>html</i></b>',
        caption_fr='france caption',
        copyright_date='2017',
        copyright_holder='CERN',
        creation_date='2017-03-02',
        directors='paperone, pluto',
        entry_date='2017-09-25',
        id=report_number,
        keywords='keyword1, keyword2',
        license_body='GPLv2',
        license_url='http://license.cern.ch',
        producer='nonna papera, zio paperino',
        record_id='1',
        title_en='My english title',
        title_fr='My french title',
        type='360 video',
        video_length=duration,
    )

    # Proper publication date
    serializer = VideoDrupal(video_record_metadata)
    data = serializer.format()['entries'][0]['entry']
    data = {k: data[k] for k in data if k in expected}
    assert data == expected

    # Empty publication date
    del video_record_metadata['publication_date']
    expected['creation_date'] = ''

    serializer = VideoDrupal(video_record_metadata)
    data = serializer.format()['entries'][0]['entry']
    data = {k: data[k] for k in data if k in expected}
    assert data == expected
