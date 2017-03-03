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
    serializer = Smil(record=rec)
    data = serializer.format()
    root = ET.fromstring(data)
    assert root.tag == 'smil'
    assert len(root[1][0]) == 4
    for child in root[1][0]:
        assert child.tag == 'video'
        assert child.attrib['system-bitrate'] == '11915822'
        assert child.attrib['width'] == '4096'
        assert child.attrib['height'] == '2160'

    for i in range(4):
        subformat = video_record_metadata['_files'][0]['subformat'][i]
        src = subformat['links']['self']
        assert root[1][0][i].attrib['src'] == 'mp4:{}'.format(src)


def test_vtt_serializer(video_record_metadata):
    """Test vtt serializer."""
    serializer = VTT(record=video_record_metadata)
    data = serializer._format_frames(video_record_metadata)
    for i in range(10):
        if i == 9:
            end_expected = VTT.time_format(float(
                video_record_metadata['_files'][0]['tags']['duration']))
            assert data[i]['end_time'] == end_expected
        else:
            assert data[i]['end_time'] == data[i + 1]['start_time']


def test_drupal_serializer(video_record_metadata, deposit_metadata):
    """Test drupal serializer."""
    duration = '00:01:00.140'
    report_number = 'RN-01'
    video_record_metadata.update(deposit_metadata)
    video_record_metadata.update({
        'report_number': {'report_number': report_number},
        '$schema': Video.get_record_schema(),
        'duration': duration,
    })
    expected = dict(
        caption_en='in tempor reprehenderit enim eiusmod',
        caption_fr='france caption',
        copyright_date='2017',
        copyright_holder='CERN',
        creation_date='2017-03-02',
        directors='paperone, pluto',
        entry_date='2016-12-03',
        id=report_number,
        keywords='keyword1, keyword2',
        license_body='GPLv2',
        license_url='http://license.cern.ch',
        producer='nonna papera, zio paperino',
        record_id=1,
        title_en='My english title',
        title_fr='My french title',
        type='video',
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
