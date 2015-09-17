# -*- coding: utf-8 -*-
#
# This file is part of Invenio
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Test cds dojson video records."""

from __future__ import absolute_import

from invenio.testsuite import InvenioTestCase, make_test_suite, run_test_suite

CDS_VIDEO_PROJECT = """
<record>
  <controlfield tag="001">2053119</controlfield>
  <controlfield tag="005">20150916121857.0</controlfield>
  <datafield tag="037" ind1=" " ind2=" ">
    <subfield code="a">CERN-MOVIE-2015-038</subfield>
  </datafield>
  <datafield tag="100" ind1=" " ind2=" ">
    <subfield code="a">CERN Video Productions</subfield>
    <subfield code="e">Produced by</subfield>
  </datafield>
  <datafield tag="245" ind1=" " ind2=" ">
    <subfield code="a">Deerhoof / Ex_noise_CERN</subfield>
  </datafield>
  <datafield tag="260" ind1=" " ind2=" ">
    <subfield code="a">2015</subfield>
  </datafield>
  <datafield tag="690" ind1="C" ind2=" ">
    <subfield code="a">publvideomovie</subfield>
  </datafield>
  <datafield tag="520" ind1=" " ind2=" ">
    <subfield code="a">Ex/Noise/CERN: experimental/noise music performance inside CERN.  It's 2015, and the Large Hadron Collider now operates at the highest energy in human history, 13 trillion electron volts. We have many ideas as to what we'll discover (dark matter, supersymmetry, extra Higgs bosons, quantum black holes), but we are really simply exploring the scientific unknown.  The participating musicians explore the musical unknown.  Ex/Noise/CERN juxtaposes physics and music by putting these musicians in CERN.</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">Deerhoof</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">SM18</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">noise</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">music</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="700" ind1=" " ind2=" ">
    <subfield code="a">Noemi Caraban</subfield>
    <subfield code="e">Director</subfield>
  </datafield>
  <datafield tag="774" ind1=" " ind2=" ">
    <subfield code="r">CERN-MOVIE-2015-038-001</subfield>
  </datafield>
  <datafield tag="859" ind1=" " ind2=" ">
    <subfield code="f">noemi.caraban.gonzalez@cern.ch</subfield>
  </datafield>
  <datafield tag="937" ind1=" " ind2=" ">
    <subfield code="c">2015-09-08</subfield>
    <subfield code="s">noemi.caraban.gonzalez@cern.ch</subfield>
  </datafield>
  <datafield tag="960" ind1=" " ind2=" ">
    <subfield code="a">85</subfield>
  </datafield>
  <datafield tag="970" ind1=" " ind2=" ">
    <subfield code="a">AVW.project.1082</subfield>
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">PUBLVIDEOMOVIE</subfield>
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="b">VIDEOMEDIALAB</subfield>
  </datafield>
</record>
"""

CDS_VIDEO_CLIP = """
<record>
  <controlfield tag="001">2053121</controlfield>
  <controlfield tag="005">20150918135611.0</controlfield>
  <datafield tag="037" ind1=" " ind2=" ">
    <subfield code="a">CERN-MOVIE-2015-038-001</subfield>
  </datafield>
  <datafield tag="041" ind1=" " ind2=" ">
    <subfield code="a">eng</subfield>
  </datafield>
  <datafield tag="110" ind1=" " ind2=" ">
    <subfield code="a">CERN, SM18, </subfield>
  </datafield>
  <datafield tag="245" ind1=" " ind2=" ">
    <subfield code="a">Ex / Noise / CERN / Deerhoof</subfield>
  </datafield>
  <datafield tag="260" ind1=" " ind2=" ">
    <subfield code="c">2015</subfield>
  </datafield>
  <datafield tag="269" ind1=" " ind2=" ">
    <subfield code="c">2015-09-15</subfield>
  </datafield>
  <datafield tag="300" ind1=" " ind2=" ">
    <subfield code="a">00:09:05.280</subfield>
    <subfield code="b">1920x1080 16/9, 25.00</subfield>
    <subfield code="c">25</subfield>
    <subfield code="d">1920x1080</subfield>
    <subfield code="e">16:9</subfield>
  </datafield>
  <datafield tag="506" ind1="1" ind2=" ">
    <subfield code="a"/>
  </datafield>
  <datafield tag="508" ind1=" " ind2=" ">
    <subfield code="a">Noemi Caraban</subfield>
  </datafield>
  <datafield tag="508" ind1=" " ind2=" ">
    <subfield code="a">Yann Krajewsky</subfield>
  </datafield>
  <datafield tag="508" ind1=" " ind2=" ">
    <subfield code="a">Piotr Traczyk</subfield>
  </datafield>
  <datafield tag="520" ind1=" " ind2=" ">
    <subfield code="a">Indie rockers Deerhoof battled with the noise of CERN’s magnet test facilities on 30 August 2015. The band visited CERN at the invitation of ATLAS physicist James Beacham, whose pilot project Ex/Noise/CERN collides experimental music artists with experimental particle physics. Credits: -Producer- CERN Video Productions James Beacham François Briard -Director- Noemi Caraban -Camera- Yann Krajewski Piotr Traczyk Noemi Caraban -Crane operator- Antonio Henrique Jorge-Costa -Live recording at CERN- Mixing at Rec studio/Geneva By Serge Morattel -Infography- Daniel Dominguez Noemi Caraban -Deerhoof- John Dieterich Satomi Matsuzaki Ed Rodriguez Greg Saunier w/Deron Pulley SPECIAL THANKS TO: Michal Strychalski Marta Bajko Maryline Charrondiere Luca Bottura Christian Giloux Rodrigue Faes Mariane Catallon Georgina Hobgen Hailey Reissman Marine Bass</subfield>
  </datafield>
  <datafield tag="542" ind1=" " ind2=" ">
    <subfield code="d">CERN</subfield>
    <subfield code="g">2015</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">satomi</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">guitar ed performance</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">bass and full band</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">cern-deerhoof-audio tracks-24 bits-48 khz</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">guitar john performance</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">noise</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">ex_noise</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">CERN</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">SM18</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">music</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
    <subfield code="a">performance</subfield>
    <subfield code="9">CERN</subfield>
  </datafield>
  <datafield tag="690" ind1="C" ind2=" ">
    <subfield code="a">publvideomovie</subfield>
  </datafield>
  <datafield tag="773" ind1=" " ind2=" ">
    <subfield code="o">AVW.project.1082</subfield>
    <subfield code="r">CERN-MOVIE-2015-038</subfield>
  </datafield>
  <datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">https://mediaarchive.cern.ch/MediaArchive/Video/Public/Movies/CERN/2015/CERN-MOVIE-2015-038/CERN-MOVIE-2015-038-001/CERN-MOVIE-2015-038-001-5872-kbps-1920x1080-audio-128-kbps-stereo.mp4</subfield>
    <subfield code="x">mp45872</subfield>
    <subfield code="y">5872 kbps maxH 1080 25 fps audio 128 kbps 48 kHz stereo</subfield>
  </datafield>
  <datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">https://mediaarchive.cern.ch/MediaArchive/Video/Public/Movies/CERN/2015/CERN-MOVIE-2015-038/CERN-MOVIE-2015-038-001/CERN-MOVIE-2015-038-001-2672-kbps-1280x720-audio-128-kbps-stereo.mp4</subfield>
    <subfield code="x">mp42672</subfield>
    <subfield code="y">2672 kbps maxH 720 25 fps audio 128 kbps 48 kHz stereo</subfield>
  </datafield>
  <datafield tag="859" ind1=" " ind2=" ">
    <subfield code="f">noemi.caraban.gonzalez@cern.ch</subfield>
  </datafield>
  <datafield tag="937" ind1=" " ind2=" ">
    <subfield code="c">18 Sep 2015</subfield>
    <subfield code="s"/>
  </datafield>
  <datafield tag="960" ind1=" " ind2=" ">
    <subfield code="a">85</subfield>
  </datafield>
  <datafield tag="970" ind1=" " ind2=" ">
    <subfield code="a">AVW.clip.1273</subfield>
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">PUBLVIDEOMOVIE</subfield>
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="b">VIDEOMEDIALAB</subfield>
  </datafield>
</record>
"""


class TestCDSDoJSONVideos(InvenioTestCase):

    """Test CDS."""

    def test_video_clip(self):
        """Test video clip loading from XML."""
        from dojson.contrib.marc21.utils import create_record
        from cds.base.dojson.cds_marc21 import cds_marc21

        blob = create_record(CDS_VIDEO_CLIP)
        data = cds_marc21.do(blob)

        # Check if the video file is present
        self.assertEqual(data.get('subject_indicator'), ['publvideomovie'])
        # Check if credits are correct
        self.assertEqual(len(data.get('creation_production_credits_note')), 3)
        # Check if the host entry is correct
        self.assertEqual(
            data['host_item_entry'][0]['report_number'],
            ["CERN-MOVIE-2015-038"]
        )
        # Check physical description
        expected_physical_description = [
            {
                "accompanying_material": "16:9",
                "other_physical_details": "1920x1080 16/9, 25.00",
                "dimensions": ["25"],
                "extent": ["00:09:05.280"]
            }
        ]
        self.assertEqual(
            data.get('physical_description'),
            expected_physical_description
        )

    def test_video_project(self):
        """Test video project from XML."""
        from dojson.contrib.marc21.utils import create_record
        from cds.base.dojson.cds_marc21 import cds_marc21

        blob = create_record(CDS_VIDEO_PROJECT)
        data = cds_marc21.do(blob)

        # Check if the video file is present
        self.assertEqual(
            data['constituent_unit_entry'][0]['report_number'],
            ['CERN-MOVIE-2015-038-001']
        )
        # Chekc the subject indicator
        self.assertEqual(data.get('subject_indicator'), ['publvideomovie'])
        # Check the control number
        self.assertEqual(data.get('control_number'), '2053119')

TEST_SUITE = make_test_suite(TestCDSDoJSONVideos)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)
