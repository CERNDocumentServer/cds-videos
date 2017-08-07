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
    url_prefix='/stats',
)


class ViewsStatsResource(MethodView):
    """Statistics of number of views resource."""

    def __init__(self):
        """Init."""
        self.read_permission_factory = record_read_permission_factory

    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, record, **kwargs):
        """Handle GET request."""
        page_views = 0
        es = Elasticsearch(CFG_ELASTICSEARCH_SEARCH_HOST)
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
        results = es.count(index=ES_INDEX, body=query)
        if results:
            page_views = results.get('count', 0)
        return make_response(jsonify(page_views), 200)


blueprint.add_url_rule(
    '/views/'
    '<pid(recid, record_class="cds.modules.records.api:CDSRecord"):pid_value>',
    view_func=ViewsStatsResource.as_view('views_stats')
)
