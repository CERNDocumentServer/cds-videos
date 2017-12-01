# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
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

"""CDS schema datacite tests."""

from __future__ import absolute_import, print_function

from invenio_records.api import Record

from cds.modules.records.serializers import datacite_v31


def test_video_metadata_tranform(app, video_record_metadata, recid_pid):
    """Test video metadata transformation."""
    video_record_metadata['doi'] = '10.1234/foo'
    obj = datacite_v31.transform_record(
        recid_pid, Record(video_record_metadata))

    expected = {
        'creators': [
            {'creatorName': 'paperone'},
            {'creatorName': 'topolino'},
            {'creatorName': 'nonna papera'},
            {'creatorName': 'pluto'},
            {'creatorName': 'zio paperino'}
        ],
        'dates': [{u'date': u'2017-03-02', u'dateType': u'Issued'}],
        'descriptions': [
            {
                'description': 'in tempor reprehenderit enim eiusmod &lt;b&gt;'
                               '<i>html</i>&lt;/b&gt;',
                'descriptionType': 'Abstract',
            }
        ],
        'identifier': {
            u'identifier': '10.1234/foo', u'identifierType': 'DOI'
        },
        'language': 'en',
        'publisher': 'CERN',
        'publicationYear': '2017',
        'resourceType': {
            'resourceTypeGeneral': 'Audiovisual', 'resourceType': None
        },
        'subjects': [
            {'subject': 'keyword1'},
            {'subject': 'keyword2'}
        ],
        'titles': [
            {u'title': u'My <b>english</b> title'}
        ],
    }
    assert expected == obj

    result = datacite_v31.serialize(
        pid=recid_pid, record=Record(video_record_metadata))
    assert '<?xml version' in result
