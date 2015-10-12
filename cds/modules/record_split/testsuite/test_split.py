# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

from __future__ import absolute_import

from cds.modules.record_split.errors import Double037FieldException

from cds.modules.record_split.photo import PhotoSplitter

from invenio.testsuite import InvenioTestCase, make_test_suite, run_test_suite


class TestPhotoSplit(InvenioTestCase):

    def test_set_record_types(self):
        album_splitter = PhotoSplitter()

        records = [{}, {}, {}]

        album_splitter._set_records_types(records[0], records[1:])

        self.assertEqual(records[0]['999__']['a'], 'ALBUM')
        self.assertEqual(records[1]['999__']['a'], 'IMAGE')
        self.assertEqual(records[2]['999__']['a'], 'IMAGE')

    def test_same_filename_same_record(self):
        album_splitter = PhotoSplitter()
        album, photos = album_splitter.split(self.xml_same_filename)

        self.assertEqual(len(photos), 1)
        self.assertEqual(len(photos[0]['8564_']), 2)
        expected = [
            {
                'u': 'http://cds.cern.ch/record/39020/files/9801023_1.gif',
            },
            {
                'u': 'http://cds.cern.ch/record/66666/files/9801023_1.gif',
            }
        ]
        self.assertEqual(photos[0]['8564_'], expected)

    def test_split_album(self):
        album_splitter = PhotoSplitter()

        album, photos = album_splitter.split(self.real_album)

        # should be 5 photos - 3 from 8564_, 2 from 8567_
        self.assertEqual(len(photos), 5)

        # check the id of album (should be unchanged)
        self.assertEqual(album['001'][0], '39020')

        # check ids of new photos
        self.assertEqual(photos[0]['001'][0], '5000000')
        self.assertEqual(photos[1]['001'][0], '5000001')
        self.assertEqual(photos[2]['001'][0], '5000002')
        self.assertEqual(photos[3]['001'][0], '5000003')
        self.assertEqual(photos[4]['001'][0], '5000004')

        # check references
        self.assertEqual(photos[0]['774__'][0], {'a': 'ALBUM', 'r': '39020'})
        self.assertEqual(photos[1]['774__'][0], {'a': 'ALBUM', 'r': '39020'})
        self.assertEqual(photos[2]['774__'][0], {'a': 'ALBUM', 'r': '39020'})
        self.assertEqual(photos[3]['774__'][0], {'a': 'ALBUM', 'r': '39020'})
        self.assertEqual(photos[4]['774__'][0], {'a': 'ALBUM', 'r': '39020'})

        self.assertEqual(album['774__'], [
            {'a': 'IMAGE', 'r': '5000000'},
            {'a': 'IMAGE', 'r': '5000001'},
            {'a': 'IMAGE', 'r': '5000002'},
            {'a': 'IMAGE', 'r': '5000003'},
            {'a': 'IMAGE', 'r': '5000004'},
        ])

        # check copied 8564_
        self.assertEqual(photos[2]['8564_'], {
            'u': 'http://cds.cern.ch/record/39020/files/9801023_1.jpeg',
            'y': 'Access to the pictures',
        })
        self.assertEqual(photos[3]['8564_'], {
            'u': 'http://cds.cern.ch/record/39020/files/9801023_2.jpeg',
            'y': 'Access to the pictures',
        })
        self.assertEqual(photos[4]['8564_'], {
            'u': 'http://cds.cern.ch/record/39020/files/9801023_3.jpeg',
            'y': 'Access to the pictures',
        })
        self.assertEqual(
            photos[0]['8567_'],
            [
                {
                    '8': '2',
                    '2': 'MediaArchive',
                    'd': r'\\cern.ch\dfs\Services\MediaArchive\Photo\Masters\1998\9801023\9801023_2.jpg',
                    'x': 'Absolute master path',
                },
                {
                    'y': 'A4 at 144 dpi',
                    '8': '2',
                    '2': 'MediaArchive',
                    'u': 'http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_2/9801023_2-A4-at-144-dpi.jpg',
                    'x': 'jpgA4',
                }
            ]
        )
        self.assertEqual(
            photos[1]['8567_'],
            [
                {
                    'y': 'A4 at 144 dpi',
                    '8': '1',
                    '2': 'MediaArchive',
                    'u': 'http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_1/9801023_1-A4-at-144-dpi.jpg',
                    'x': 'jpgA4',
                },
                {
                    'y': 'A5 at 72 dpi',
                    '8': '1',
                    '2': 'MediaArchive',
                    'u': 'http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_1/9801023_1-A5-at-72-dpi.jpg',
                    'x': 'jpgA5',
                }
            ]
        )

        expected_fields_8564 = {
            '037__': {'a': 'CERN-AC-9801023-01'},
            '100__': {'a': 'Laurent Guiraud'},
            '260__': {'c': '1998'},
            '269__': {'c': 'Jan 1998'},
            '542__': {'d': 'CERN', 'g': '1998'},
        }

        # check identifier for 8564 based records
        for photo in photos[2:]:
            self.assertEqual(photo['037__'], expected_fields_8564['037__'])
            self.assertEqual(photo['100__'], expected_fields_8564['100__'])
            self.assertEqual(photo['260__'], expected_fields_8564['260__'])
            self.assertEqual(photo['269__'], expected_fields_8564['269__'])
            self.assertEqual(photo['542__'], expected_fields_8564['542__'])

        expected_fields_8567_1 = {
            '037__': {'a': 'CERN-AC-9801023-2'},
            '100__': {'a': 'Laurent Guiraud'},
            '260__': {'c': '1998'},
            '269__': {'c': 'Jan 1998'},
            '542__': {'d': 'CERN', 'g': '1998'},
        }

        expected_fields_8567_2 = {
            '037__': {'a': 'CERN-AC-9801023-1'},
            '100__': {'a': 'Laurent Guiraud'},
            '260__': {'c': '1998'},
            '269__': {'c': 'Jan 1998'},
            '542__': {'d': 'CERN', 'g': '1998'},
        }
        # check identifier for 8567 based records

        self.assertEqual(photos[0]['037__'], expected_fields_8567_1['037__'])
        self.assertEqual(photos[0]['100__'], expected_fields_8567_1['100__'])
        self.assertEqual(photos[0]['260__'], expected_fields_8567_1['260__'])
        self.assertEqual(photos[0]['269__'], expected_fields_8567_1['269__'])
        self.assertEqual(photos[0]['542__'], expected_fields_8567_1['542__'])

        self.assertEqual(photos[1]['037__'], expected_fields_8567_2['037__'])
        self.assertEqual(photos[1]['100__'], expected_fields_8567_2['100__'])
        self.assertEqual(photos[1]['260__'], expected_fields_8567_2['260__'])
        self.assertEqual(photos[1]['269__'], expected_fields_8567_2['269__'])
        self.assertEqual(photos[1]['542__'], expected_fields_8567_2['542__'])

        # does it remove 8564_
        # self.assertEqual(len(splitted_album[0]['8564_']), 0)

        # does it remove the icons
        self.assertIsNone(album.get('8564_'))

    def test_exception_when_record_malformed(self):
        album_splitter = PhotoSplitter()
        self.assertRaises(AssertionError,
                          album_splitter.split_records_string,
                          self.real_album_exc)

    def test_no_exception_when_record_legacy(self):
        album_splitter = PhotoSplitter()
        album_splitter.split_records_string(self.real_album_legacy)

    def test_malformed_037_field(self):
        album_splitter = PhotoSplitter()
        self.assertRaises(Double037FieldException,
                          album_splitter.split_records_string,
                          self.xml_037_malformed)

    xml_037_malformed = """
        <record>
            <controlfield tag="001">39019</controlfield>
            <controlfield tag="003">SzGeCERN</controlfield>
            <controlfield tag="005">20131213180302.0</controlfield>
            <datafield tag="035" ind1=" " ind2=" ">
                <subfield code="9">PHOPHO</subfield>
                <subfield code="a">0000101</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008-dummy</subfield>
            </datafield>
            <datafield tag="856" ind1="4" ind2=" ">
                <subfield code="u">http://cds.cern.ch/record/66666/files/9801023_1.gif</subfield>
            </datafield>
        </record>
    """

    xml_same_filename = """
        <record>
            <controlfield tag="001">39019</controlfield>
            <controlfield tag="003">SzGeCERN</controlfield>
            <controlfield tag="005">20131213180302.0</controlfield>
            <datafield tag="035" ind1=" " ind2=" ">
                <subfield code="9">PHOPHO</subfield>
                <subfield code="a">0000101</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008</subfield>
            </datafield>
            <datafield tag="041" ind1=" " ind2=" ">
                <subfield code="a">ENG</subfield>
            </datafield>
            <datafield tag="245" ind1=" " ind2=" ">
                <subfield code="a">A diagram of the CERN accelerator complex.</subfield>
            </datafield>
            <datafield tag="856" ind1="4" ind2=" ">
                <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.gif</subfield>
            </datafield>
            <datafield tag="856" ind1="4" ind2=" ">
                <subfield code="u">http://cds.cern.ch/record/66666/files/9801023_1.gif</subfield>
            </datafield>
        </record>
    """

    xml_album = """
        <record>
            <controlfield tag="001">39019</controlfield>
            <controlfield tag="003">SzGeCERN</controlfield>
            <controlfield tag="005">20131213180302.0</controlfield>
            <datafield tag="035" ind1=" " ind2=" ">
                <subfield code="9">PHOPHO</subfield>
                <subfield code="a">0000101</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008</subfield>
            </datafield>
            <datafield tag="041" ind1=" " ind2=" ">
                <subfield code="a">ENG</subfield>
            </datafield>
            <datafield tag="245" ind1=" " ind2=" ">
                <subfield code="a">A diagram of the CERN accelerator complex.</subfield>
            </datafield>
            <datafield tag="856" ind1="4" ind2=" ">
                <subfield code="q">http://preprints.cern.ch/cgi-bin/setlink?base=PHO&amp;categ=photo-di&amp;id=9704008</subfield>
                <subfield code="x">1</subfield>
                <subfield code="y">Access to the pictures</subfield>
            </datafield>
        </record>
    """

    xml_photo = """
        <record>
            <controlfield tag="001">39020</controlfield>
            <controlfield tag="003">SzGeCERN</controlfield>
            <controlfield tag="005">20131213180302.0</controlfield>
            <datafield tag="035" ind1=" " ind2=" ">
                <subfield code="9">PHOPHO</subfield>
                <subfield code="a">0000101</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008</subfield>
            </datafield>
            <datafield tag="041" ind1=" " ind2=" ">
                <subfield code="a">ENG</subfield>
            </datafield>
            <datafield tag="245" ind1=" " ind2=" ">
                <subfield code="a">A diagram of the CERN accelerator complex.</subfield>
            </datafield>
        </record>
    """

    xml_record = """
        <record>
            <controlfield tag="001">39019</controlfield>
            <controlfield tag="003">SzGeCERN</controlfield>
            <controlfield tag="005">20131213180302.0</controlfield>
            <datafield tag="035" ind1=" " ind2=" ">
                <subfield code="9">PHOPHO</subfield>
                <subfield code="a">0000101</subfield>
            </datafield>
            <datafield tag="037" ind1=" " ind2=" ">
                <subfield code="a">CERN-DI-9704008</subfield>
            </datafield>
            <datafield tag="041" ind1=" " ind2=" ">
                <subfield code="a">ENG</subfield>
            </datafield>
            <datafield tag="245" ind1=" " ind2=" ">
                <subfield code="a">A diagram of the CERN accelerator complex.</subfield>
            </datafield>
        </record>
    """

    dict_record = {
        u'001': ['39019'],
        u'003': ['SzGeCERN'],
        u'005': ['20131213180302.0'],
        u'035__': {
            'a': '0000101',
            '9': 'PHOPHO'
        },
        u'037__': {
            'a': 'CERN-DI-9704008'
        },
        u'041__': {
            'a': 'ENG'
        },
        u'245__': {
            'a': 'A diagram of the CERN accelerator complex.'
        }
    }

    real_album = r"""
        <record>
          <controlfield tag="001">39020</controlfield>
          <controlfield tag="003">SzGeCERN</controlfield>
          <controlfield tag="005">20131213180305.0</controlfield>
          <datafield tag="024" ind1="8" ind2=" ">
            <subfield code="a">oai:cds.cern.ch:39020</subfield>
            <subfield code="p">cerncds:FULLTEXT</subfield>
          </datafield>
          <datafield tag="035" ind1=" " ind2=" ">
            <subfield code="9">PHOPHO</subfield>
            <subfield code="a">0000102</subfield>
          </datafield>
          <datafield tag="037" ind1=" " ind2=" ">
            <subfield code="a">CERN-AC-9801023</subfield>
          </datafield>
          <datafield tag="100" ind1=" " ind2=" ">
            <subfield code="a">Laurent Guiraud</subfield>
          </datafield>
          <datafield tag="246" ind1=" " ind2="1">
            <subfield code="a">Introduction tube long 32 m dans tube faisceau sur le string au SM18</subfield>
          </datafield>
          <datafield tag="260" ind1=" " ind2=" ">
            <subfield code="c">1998</subfield>
          </datafield>
          <datafield tag="269" ind1=" " ind2=" ">
            <subfield code="c">Jan 1998</subfield>
          </datafield>
          <datafield tag="340" ind1=" " ind2=" ">
            <subfield code="a">DIA Coul 35</subfield>
          </datafield>
          <datafield tag="542" ind1=" " ind2=" ">
            <subfield code="d">CERN</subfield>
            <subfield code="g">1998</subfield>
          </datafield>
          <datafield tag="650" ind1="1" ind2="7">
            <subfield code="2">SzGeCERN</subfield>
            <subfield code="a">Accelerators</subfield>
          </datafield>
          <datafield tag="653" ind1="1" ind2=" ">
            <subfield code="9">CERN</subfield>
            <subfield code="a">LHC</subfield>
          </datafield>
          <datafield tag="916" ind1=" " ind2=" ">
            <subfield code="s">n</subfield>
            <subfield code="w">199800</subfield>
          </datafield>
          <datafield tag="923" ind1=" " ind2=" ">
            <subfield code="r">Moiroux, R</subfield>
          </datafield>
          <datafield tag="923" ind1=" " ind2=" ">
            <subfield code="p">SM18</subfield>
          </datafield>
          <datafield tag="960" ind1=" " ind2=" ">
            <subfield code="a">81</subfield>
          </datafield>
          <datafield tag="961" ind1=" " ind2=" ">
            <subfield code="c">20050511</subfield>
            <subfield code="h">1436</subfield>
            <subfield code="l">MMD01</subfield>
            <subfield code="x">19970828</subfield>
          </datafield>
          <datafield tag="963" ind1=" " ind2=" ">
            <subfield code="a">PUBLIC</subfield>
          </datafield>
          <datafield tag="980" ind1=" " ind2=" ">
            <subfield code="a">PHOTOLAB</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="8">2</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="d">\\cern.ch\dfs\Services\MediaArchive\Photo\Masters\1998\9801023\9801023_2.jpg</subfield>
            <subfield code="x">Absolute master path</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="y">A4 at 144 dpi</subfield>
            <subfield code="8">2</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="u">http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_2/9801023_2-A4-at-144-dpi.jpg</subfield>
            <subfield code="x">jpgA4</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="y">A4 at 144 dpi</subfield>
            <subfield code="8">1</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="u">http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_1/9801023_1-A4-at-144-dpi.jpg</subfield>
            <subfield code="x">jpgA4</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="y">A5 at 72 dpi</subfield>
            <subfield code="8">1</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="u">http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_1/9801023_1-A5-at-72-dpi.jpg</subfield>
            <subfield code="x">jpgA5</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.jpeg</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_2.jpeg</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_3.jpeg</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.jpeg?subformat=icon-180</subfield>
            <subfield code="x">icon-180</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.jpeg?subformat=icon-640</subfield>
            <subfield code="x">icon-640</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_2.jpeg?subformat=icon-1440</subfield>
            <subfield code="x">icon-1440</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_2.jpeg?subformat=icon-640</subfield>
            <subfield code="x">icon-640</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_3.jpeg?subformat=icon-640</subfield>
            <subfield code="x">icon-640</subfield>
          </datafield>
          <datafield tag="970" ind1=" " ind2=" ">
            <subfield code="a">000000102MMD</subfield>
          </datafield>
        </record>
    """

    real_album_exc = r"""
        <record>
          <controlfield tag="001">39020</controlfield>
          <controlfield tag="003">SzGeCERN</controlfield>
          <controlfield tag="005">20131213180305.0</controlfield>
          <datafield tag="024" ind1="8" ind2=" ">
            <subfield code="a">oai:cds.cern.ch:39020</subfield>
            <subfield code="p">cerncds:FULLTEXT</subfield>
          </datafield>
          <datafield tag="035" ind1=" " ind2=" ">
            <subfield code="9">PHOPHO</subfield>
            <subfield code="a">0000102</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="8">2</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="d">\\cern.ch\dfs\Services\MediaArchive\Photo\Masters\1998\9801023\9801023_2.jpg</subfield>
            <subfield code="x">Absolute master path</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="2">MediaArchive</subfield>
            <subfield code="8">3</subfield>
            <subfield code="u">http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_3/9801023_3-Icon.jpg</subfield>
            <subfield code="x">jpgIcon</subfield>
            <subfield code="y">Icon</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="q">http://dummypreprints.cern.ch/photo/photo-ac/9801023_1.gif</subfield>
            <subfield code="x">icon</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="q">http://dummypreprints.cern.ch/cgi-bin/setlink?base=PHO&amp;categ=photo-ac&amp;id=9801023</subfield>
            <subfield code="x">1</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.jpeg</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_3.jpeg?subformat=icon-640</subfield>
            <subfield code="x">icon-640</subfield>
          </datafield>
          <datafield tag="970" ind1=" " ind2=" ">
            <subfield code="a">000000102MMD</subfield>
          </datafield>
        </record>
    """

    real_album_legacy = r"""
        <record>
          <controlfield tag="001">39020</controlfield>
          <controlfield tag="003">SzGeCERN</controlfield>
          <controlfield tag="005">20131213180305.0</controlfield>
          <datafield tag="024" ind1="8" ind2=" ">
            <subfield code="a">oai:cds.cern.ch:39020</subfield>
            <subfield code="p">cerncds:FULLTEXT</subfield>
          </datafield>
          <datafield tag="035" ind1=" " ind2=" ">
            <subfield code="9">PHOPHO</subfield>
            <subfield code="a">0000102</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="8">2</subfield>
            <subfield code="2">MediaArchive</subfield>
            <subfield code="d">\\cern.ch\dfs\Services\MediaArchive\Photo\Masters\1998\9801023\9801023_2.jpg</subfield>
            <subfield code="x">Absolute master path</subfield>
          </datafield>
          <datafield tag="856" ind1="7" ind2=" ">
            <subfield code="2">MediaArchive</subfield>
            <subfield code="8">3</subfield>
            <subfield code="u">http://mediaarchive.cern.ch/MediaArchive/Photo/Public/1998/9801023/9801023_3/9801023_3-Icon.jpg</subfield>
            <subfield code="x">jpgIcon</subfield>
            <subfield code="y">Icon</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="q">http://preprints.cern.ch/photo/photo-ac/9801023_1.gif</subfield>
            <subfield code="x">icon</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="q">http://preprints.cern.ch/cgi-bin/setlink?base=PHO&amp;categ=photo-ac&amp;id=9801023</subfield>
            <subfield code="x">1</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_1.jpeg</subfield>
            <subfield code="y">Access to the pictures</subfield>
          </datafield>
          <datafield tag="856" ind1="4" ind2=" ">
            <subfield code="u">http://cds.cern.ch/record/39020/files/9801023_3.jpeg?subformat=icon-640</subfield>
            <subfield code="x">icon-640</subfield>
          </datafield>
          <datafield tag="970" ind1=" " ind2=" ">
            <subfield code="a">000000102MMD</subfield>
          </datafield>
        </record>
    """

TEST_SUITE = make_test_suite(TestPhotoSplit)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)
