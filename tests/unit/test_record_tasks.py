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

"""Test record tasks."""

from __future__ import absolute_import, print_function

import json
from time import sleep

import mock
from helpers import create_keyword, get_indexed_records_from_mock
from invenio_indexer.api import RecordIndexer
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from invenio_search import current_search_client

from cds.modules.records.api import Keyword
from cds.modules.records.search import KeywordSearch, query_to_objects
from cds.modules.records.tasks import (
    _delete_not_existing_keywords,
    _get_keywords_from_api,
    _update_existing_keywords,
    keywords_harvesting,
)


def test_get_keywords_from_api(cern_keywords):
    """Test get keywords from API."""
    url = 'test'
    return_value = type(url, (object, ), {
        'text': json.dumps(cern_keywords)}
    )
    with mock.patch('requests.get', return_value=return_value):
        keywords = _get_keywords_from_api(url)
        expected = {
            '751': dict(name='13 TeV',
                        provenance=url),
            '856': dict(name='Accelerating News',
                        provenance=url),
            '97': dict(name='accelerator',
                       provenance=url),
            '14': dict(name='AEGIS',
                       provenance=url),
        }
        assert expected == keywords


def test_update_existing_keywords(cern_keywords, location):
    """Test update existing keywords on db."""
    keywords = [
        # 1: unchanged
        {'key_id': '751',
         'name': '13 TeV',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 2: changed
        {'key_id': '856',
         'name': 'test-changed',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 3: already deleted
        {'key_id': '21',
         'name': 'ACE',
         'deleted': True,
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 4: restored
        {'key_id': '14',
         'name': 'AEGIS',
         'deleted': True,
         'provenance': 'http://home.cern/api/tags-json-feed'},
    ]
    keywords_db = []
    for keyword in keywords:
        keywords_db.append(create_keyword(data=keyword))
    assert RecordMetadata.query.count() == 4
    # keyword harvested
    keywords_api = {
        '751': dict(name='13 TeV',
                    provenance='http://home.cern/api/tags-json-feed'),
        '856': dict(name='Accelerating News',
                    provenance='http://home.cern/api/tags-json-feed'),
        '97': dict(name='accelerator',
                   provenance='http://home.cern/api/tags-json-feed'),
        '14': dict(name='AEGIS',
                   provenance='http://home.cern/api/tags-json-feed'),
    }
    indexer = type('indexer', (object, ), {})
    indexer.bulk_index = mock.Mock()
    _update_existing_keywords(indexer=indexer,
                              keywords_api=keywords_api,
                              keywords_db=keywords_db)
    assert indexer.bulk_index.called
    # 1 modified + 1 created + 1 restored
    ids = get_indexed_records_from_mock(indexer.bulk_index)
    assert len(ids) == 3
    # 2 existing + 1 created + 1 deleted + 1 restored
    records = RecordMetadata.query.all()
    assert len(records) == 5
    # This test becomes hackish, so I would remove it in the future
    ks = {k.json['key_id']:
          dict(name=k.json['name'],
               provenance=k.json['provenance']) for k in records}
    # count also the deleted key
    keywords_api['21'] = {
        'name': 'ACE',
        'provenance': 'http://home.cern/api/tags-json-feed'
    }
    assert keywords_api == ks


def test_delete_not_existing_keywords(cern_keywords, location):
    """Test delete not existing keywords on db."""
    keywords = [
        # 1: unchanged
        {'key_id': '751', 'name': '13 TeV'},
        # 2: deleted
        {'key_id': '856', 'name': 'test-deleted'},
    ]
    keywords_db = []
    for keyword in keywords:
        keywords_db.append(create_keyword(data=keyword))
    assert RecordMetadata.query.count() == 2
    # keyword harvested
    keywords_api = {
        '751': '13 TeV',
    }
    indexer = type('indexer', (object, ), {})
    indexer.bulk_index = mock.Mock()
    _delete_not_existing_keywords(indexer=indexer,
                                  keywords_api=keywords_api,
                                  keywords_db=keywords_db)
    assert indexer.bulk_index.called
    # 1 keyword deleted
    ids = get_indexed_records_from_mock(indexer.bulk_index)
    assert len(ids) == 1
    records = RecordMetadata.query.filter_by(id=ids[0]).all()
    assert len(records) == 1
    assert records[0].json['key_id'] == '856'
    assert records[0].json['name'] == 'test-deleted'
    # 1 existing keyword only
    records = RecordMetadata.query.filter(RecordMetadata.id != ids[0]).all()
    assert len(records) == 1
    assert records[0].json['key_id'] == '751'
    assert records[0].json['name'] == '13 TeV'


def test_keyword_harvesting_one_time(db, cern_keywords, location):
    """Test keyword harvesting."""
    keywords = [
        # 1: unchanged
        {'key_id': '751',
         'name': '13 TeV',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 2: changed
        {'key_id': '856',
         'name': 'test-changed',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 3: deleted
        {'key_id': '532',
         'name': 'ACCU',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 4: already deleted
        {'key_id': '21',
         'name': 'ACE',
         'deleted': True,
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 5: restored
        {'key_id': '14',
         'name': 'AEGIS',
         'deleted': True,
         'provenance': 'http://home.cern/api/tags-json-feed'},
    ]
    keywords_db = []
    for keyword in keywords:
        keywords_db.append(create_keyword(data=keyword))
    assert RecordMetadata.query.count() == 5
    current_search_client.indices.refresh()
    return_value = type('test', (object, ), {
        'text': json.dumps(cern_keywords)}
    )
    with mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_bulk_index, \
            mock.patch('requests.get', return_value=return_value):
        keywords_harvesting.s().apply()
    # assert 4 keywords are updated(1 update + 1 new + 1 restored + 1 deleted)
    assert mock_bulk_index.called
    ids = get_indexed_records_from_mock(mock_bulk_index)
    records = RecordMetadata.query.filter(RecordMetadata.id.in_(ids)).all()
    jsons = {record.json['key_id']: record.json for record in records}
    keys = jsons.keys()
    assert len(keys) == 4
    assert '856' in keys
    assert jsons['856']['name'] == 'Accelerating News'
    assert jsons['856']['deleted'] is False
    assert '97' in keys
    assert jsons['97']['name'] == 'accelerator'
    assert jsons['97']['deleted'] is False
    assert '14' in keys
    assert jsons['14']['name'] == 'AEGIS'
    assert jsons['14']['deleted'] is False
    assert jsons['532']['key_id'] == '532'
    assert jsons['532']['name'] == 'ACCU'
    assert jsons['532']['deleted'] is True


def test_keyword_harvesting_deleted_keywords(db, cern_keywords, location):
    """Test keyword harvesting."""
    keywords = [
        # 1: unchanged
        {'key_id': '751',
         'name': '13 TeV',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 2: unchanged
        {'key_id': '856',
         'name': 'Accelerating News',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 3: deleted
        {'key_id': '532',
         'name': 'ACCU',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 4: unchanged
        {'key_id': '97',
         'name': 'accelerator',
         'provenance': 'http://home.cern/api/tags-json-feed'},
        # 6: unchanged
        {'key_id': '14',
         'name': 'AEGIS',
         'provenance': 'http://home.cern/api/tags-json-feed'},
    ]
    keywords_db = []
    for keyword in keywords:
        keywords_db.append(create_keyword(data=keyword))
    assert RecordMetadata.query.count() == 5
    current_search_client.indices.refresh()
    return_value = type('test', (object, ), {
        'text': json.dumps(cern_keywords)}
    )
    with mock.patch('invenio_indexer.api.RecordIndexer.bulk_index') \
            as mock_bulk_index, \
            mock.patch('requests.get', return_value=return_value):
        keywords_harvesting.s().apply()

        # check if 1 keyword is deleted
        assert mock_bulk_index.called
        ids = get_indexed_records_from_mock(mock_bulk_index)
        assert len(ids) == 1
        deleted = Record.get_record(ids[0])
        #  deleted = RecordMetadata.query.filter_by(id=ids[0]).first()

    RecordIndexer().index(deleted)
    current_search_client.indices.refresh()

    # restore a key
    cern_keywords['tags'].append({
        'id': deleted['key_id'], 'name': deleted['name']
    })

    return_value = type('test', (object, ), {
        'text': json.dumps(cern_keywords)}
    )
    with mock.patch('invenio_indexer.api.RecordIndexer.bulk_index'), \
            mock.patch('requests.get', return_value=return_value):
        # run again
        keywords_harvesting.s().apply()
        sleep(1)

        keywords_es = query_to_objects(
            query=KeywordSearch().params(version=True), cls=Keyword)
        keywords_db = [k.json for k in RecordMetadata.query.all()]
        sorted_db = sorted(keywords_db, key=lambda x: x['key_id'])
        sorted_es = sorted(keywords_es, key=lambda x: x['key_id'])
        assert sorted_es == sorted_db
