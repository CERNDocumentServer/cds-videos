# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from __future__ import absolute_import

import sys
from json import dumps
from elasticsearch import Elasticsearch, ConnectionError, TransportError, \
    RequestError
from flask import Response
from functools import wraps

from invenio.base.decorators import wash_arguments
from ..config import CFG_ES_SEARCH_HOSTS, \
    CFG_ES_SEARCH_INDEX_PREFIX, STATS_CFG

elasticsearch = Elasticsearch(hosts=CFG_ES_SEARCH_HOSTS)
ES_INDEX = CFG_ES_SEARCH_INDEX_PREFIX + '*'
DEFAULT_TERMS_SIZE = 10


def _error_decorator(f):
    @wraps(f)
    def _decorator(*args, **kwargs):
        try:
            json = dumps(f(*args, **kwargs))
            resp = Response(json, status=200, mimetype='application/json')
        except (ConnectionError, TransportError, RequestError) as e:
            if type(e.status_code) == int:
                status = e.status_code
            else:
                status = 500
            error = dumps(e.error)
            resp = Response(error, status=status, mimetype='application/json')
        # TODO: refactor this into general case when we have data sources other
        # than ES.
        except KeyError as e:
            error = dumps("No such key: " + str(e.args[0]))
            resp = Response(error, status=400, mimetype='application/json')
            raise e
        return resp
    return _decorator


def _gen_time_filter(**kwargs):
    time_from_valid = 'time_from' in kwargs and kwargs['time_from'] is not None
    time_to_valid = 'time_to' in kwargs and kwargs['time_to'] is not None
    if time_from_valid and time_to_valid:
        filters = {
            'range': {
                '@timestamp': {
                    'gte': kwargs['time_from'],
                    'lte': kwargs['time_to']
                }
            }
        }
    else:
        filters = None
    return filters


def _gen_rec_id_filter(rec_id_field, **kwargs):
    if 'rec_id' in kwargs and kwargs['rec_id'] is not None:
        filters = {
            'query': {
                'match': {
                    rec_id_field: kwargs['rec_id']
                }
            }
        }
    else:
        filters = None
    return filters


def histogram(f):
    @wraps(f)
    @_error_decorator
    @wash_arguments({'name': (unicode, None),
                     'interval': (unicode, None),
                     'time_from': (unicode, None),
                     'time_to': (unicode, None),
                     'rec_id': (int, None)})
    def _decorator(**kwargs):
        name = kwargs['name']
        event = STATS_CFG['events'][name]
        rec_id_field = event['params']['rec_id_field']
        rec_id_filter = _gen_rec_id_filter(rec_id_field=rec_id_field, **kwargs)

        time_filter = _gen_time_filter(**kwargs)

        if rec_id_filter is not None:
            if time_filter is not None:
                filters = {'and': [rec_id_filter, time_filter]}
            else:
                filters = rec_id_filter
        else:
            filters = time_filter
        return f(filters=filters, **kwargs)
    return _decorator


def terms(f):
    @wraps(f)
    @_error_decorator
    @wash_arguments({'name': (unicode, None),
                     'field': (unicode, None),
                     'size': (unicode, DEFAULT_TERMS_SIZE),
                     'time_from': (unicode, None),
                     'time_to': (unicode, None),
                     'rec_id': (int, None)})
    def _decorator(**kwargs):
        # TODO: refactor this with _decorator from histogram() function above.
        name = kwargs['name']
        event = STATS_CFG['events'][name]
        rec_id_field = event['params']['rec_id_field']
        rec_id_filter = _gen_rec_id_filter(rec_id_field=rec_id_field, **kwargs)

        time_filter = _gen_time_filter(**kwargs)

        if rec_id_filter is not None:
            if time_filter is not None:
                filters = {'and': [rec_id_filter, time_filter]}
            else:
                filters = rec_id_filter
        else:
            filters = time_filter
        return f(filters=filters, **kwargs)
    return _decorator


def _get_buckets(query, aggregation, doc_type, filters):
    if filters is not None:
        query['query'] = {'constant_score': {'filter': filters}}
    raw_result = elasticsearch.search(index=ES_INDEX,
                                      doc_type=doc_type,
                                      body=query,
                                      _source=False)

    hits = raw_result['hits']['total']
    buckets = raw_result['aggregations'][aggregation]['buckets']
    return (hits, buckets)


def get_histogram(doc_type, interval, time_field='@timestamp', filters=None,
                  **kwargs):
    query = {
        'aggregations': {
            'by_date': {
                'date_histogram': {
                    'field': time_field,
                    'interval': interval,
                    'min_doc_count': 0
                }
            }
        }
    }
    return _get_buckets(query, 'by_date', doc_type, filters)


def get_terms(doc_type, field, size, filters=None,
              **kwargs):
    query = {
        'aggregations': {
            'by_term': {
                'terms': {
                    'field': field,
                    'size': size
                }
            }
        }
    }
    return _get_buckets(query, 'by_term', doc_type, filters)
