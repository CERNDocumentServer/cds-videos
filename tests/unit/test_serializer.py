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

import xml.etree.ElementTree as ET

from cds.modules.records.serializers.smil import Smil
from cds.modules.records.serializers.vtt import VTT


def test_smil_serializer(video_metadata):
    """Test smil serializer."""
    rec = video_metadata
    serializer = Smil(record=rec)
    data = serializer.format()
    root = ET.fromstring(data)
    assert root.tag == 'smil'
    assert len(root[1][0]) == 4
    for child in root[1][0]:
        assert child.tag == 'video'
        assert child.attrib["system-bitrate"] == '11915822'
        assert child.attrib["width"] == '4096'
        assert child.attrib["height"] == '2160'

    src1 = video_metadata['_files'][0]['video'][0]['links']['self']
    src2 = video_metadata['_files'][0]['video'][1]['links']['self']
    src3 = video_metadata['_files'][0]['video'][2]['links']['self']
    src4 = video_metadata['_files'][0]['video'][3]['links']['self']

    assert root[1][0][0].attrib['src'] == src1
    assert root[1][0][1].attrib['src'] == src2
    assert root[1][0][2].attrib['src'] == src3
    assert root[1][0][3].attrib['src'] == src4


def test_vtt_serializer(video_metadata):
    """Test vtt serializer"""
    serializer = VTT(record=video_metadata)
    data = serializer.format()
    print (data)
    # root = ET.fromstring(data)
    # assert root.tag == 'smil'
    # assert len(root[1][0]) == 4
    # for child in root[1][0]:
    #     assert child.tag == 'video'
    #     assert child.attrib["system-bitrate"] == '11915822'
    #     assert child.attrib["width"] == '4096'
    #     assert child.attrib["height"] == '2160'
