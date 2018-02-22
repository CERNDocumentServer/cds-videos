# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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

"""CDS Stats."""

from __future__ import absolute_import, print_function

from elasticsearch import Elasticsearch

from flask import Blueprint, jsonify, make_response
from flask.views import MethodView

from cds.modules.records.permissions import record_read_permission_factory
from invenio_records_rest.views import pass_record, need_record_permission

# Legaciy code: once invenio-statistics is used, this code will be removed.
CFG_ELASTICSEARCH_SEARCH_HOST = [{'host': '127.0.0.1', 'port': 9199}]
ES_INDEX = 'cds-*'

blueprint = Blueprint(
    'cds_stats',
    __name__,
    url_prefix='/stats/',
)


class StatsResource(MethodView):
    """Statistics of resources."""

    def __init__(self):
        """Init."""
        self.read_permission_factory = record_read_permission_factory

    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, stat, record, **kwargs):
        """Handle GET request."""

        report_number = record.get('report_number')[0]
        es = Elasticsearch(CFG_ELASTICSEARCH_SEARCH_HOST)
        query = {}
        results = {}

        # Get total number of pageviews for a specific CDS record
        if stat == 'views':
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "id_bibrec": pid.pid_value
                                }
                            },
                            {
                                "match": {
                                    "_type": "events.pageviews"
                                }
                            }
                        ]
                    }
                }
            }
            results = es.count(index=ES_INDEX, body=query).get('count', 0)

        # Get timestamp-aggregated downloads for specific CDS record
        elif stat == 'downloads':
            key_type = 'date'
            query = {
                "query": {
                    "filtered": {
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "match": {
                                            "file": report_number
                                        }
                                    },
                                    {
                                        "match": {
                                            "_type": "events.media_download"
                                        }
                                    }
                                ]
                            }
                        },
                        "filter": {
                            "range": {
                                "@timestamp": {
                                    "from": 0,
                                    "to": "now"
                                }
                            }
                        }
                    }
                },
                "aggregations": {
                    "by_time": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "interval": "day"
                        }
                    }
                }
            }
            results = self.transform(
                es.search(index=ES_INDEX, body=query),
                stat,
                key_type)

        # Get timestamp-aggregated pageviews for specific CDS record
        elif stat == 'pageviews':
            key_type = 'date'
            query = {
                "query": {
                    "filtered": {
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "match": {
                                            "id_bibrec": pid.pid_value
                                        }
                                    },
                                    {
                                        "match": {
                                            "_type": "events.pageviews"
                                        }
                                    }
                                ]
                            }
                        },
                        "filter": {
                            "range": {
                                "@timestamp": {
                                    "from": 0,
                                    "to": "now"
                                }
                            }
                        }
                    }
                },
                "aggregations": {
                    "by_time": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "interval": "day"
                        }
                    }
                }
            }
            results = self.transform(
                es.search(index=ES_INDEX, body=query),
                stat,
                key_type)

        return make_response(jsonify(results), 200)

    # Convert retrieved statistics into 'Invenio-Stats' format
    def transform(self, response, metric, key_type):
        graph_data = {}
        graph_data[metric] = {}
        graph_data[metric]['buckets'] = []
        graph_data[metric]['type'] = 'bucket'
        if key_type == 'date':
            # This is a time query
            graph_data[metric]['key_type'] = 'date'
            graph_data[metric]['interval'] = 'month'
        else:
            # This is a non-time query
            graph_data[metric]['key_type'] = 'other'
        for entry in response['aggregations']['by_time']['buckets']:
            temp = {}
            temp['key'] = entry['key']
            temp['value'] = entry['doc_count']
            # 'buckets' array holds the input data passed to the graph
            graph_data[metric]['buckets'].append(temp)
        return graph_data


blueprint.add_url_rule(
    '<pid(recid, record_class="cds.modules.records.api:CDSRecord"):pid_value>/'
    '<stat>',
    view_func=StatsResource.as_view('record_stats')
)
