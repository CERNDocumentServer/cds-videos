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
from webargs.flaskparser import use_kwargs
from webargs import fields

from cds.modules.records.permissions import record_read_permission_factory
from flask import Blueprint, current_app, jsonify, make_response
from flask.views import MethodView
from invenio_records_rest.views import need_record_permission, pass_record

from cds.modules.stats.event_builders import file_download_event_builder

from .api import Statistics

# Legaciy code: once invenio-statistics is used, this code will be removed.
ES_INDEX = "cds-*"

blueprint = Blueprint(
    "cds_stats",
    __name__,
    url_prefix="/stats/",
)


from blinker import Namespace

_signals = Namespace()


cds_record_viewed = _signals.signal("cds-record-viewed")
cds_record_media_viewed = _signals.signal("cds-record-media-viewed")
cds_record_media_downloaded = _signals.signal("cds-record-media-downloaded")


class StatsResource(MethodView):
    """Statistics of resources."""

    def __init__(self):
        """Init."""
        self.read_permission_factory = record_read_permission_factory

    @staticmethod
    def _build_subquery(report_number):
        """OpenSearch subquery for download statistics.
        Because the report number was changed for consistency reasons,
        we had to build a workaround so that we can target old videos
        by report number.

        :param report_number: the report number of a record
        """

        if "VIDEO" in report_number:
            report_number_movie = report_number.replace("VIDEO", "MOVIE")
            report_number_videoclip = report_number.replace("VIDEO", "VIDEOCLIP")
            subquery = {
                "should": [
                    {"match": {"file": report_number}},
                    {"match": {"file": report_number_movie}},
                    {"match": {"file": report_number_videoclip}},
                    {"match": {"_type": "events.cds_videos_media_download"}},
                ],
                "minimum_should_match": 2,
            }

        if "FOOTAGE" in report_number:
            report_number_videorush = report_number.replace("FOOTAGE", "VIDEORUSH")
            subquery = {
                "should": [
                    {"match": {"file": report_number}},
                    {"match": {"file": report_number_videorush}},
                    {"match": {"_type": "events.cds_videos_media_download"}},
                ],
                "minimum_should_match": 2,
            }
        return subquery

    @pass_record
    @need_record_permission("read_permission_factory")
    def get(self, pid, record, **kwargs):
        """Handle GET request."""
        # es = OpenSearch([{
        #     'host': current_app.config['LEGACY_STATS_ELASTIC_HOST'],
        #     'port': current_app.config['LEGACY_STATS_ELASTIC_PORT'],
        # }])
        # query = {}
        # results = {}

        # # Get total number of pageviews for a specific CDS record
        # if stat == 'views':
        #     query = {
        #         "query": {
        #             "bool": {
        #                 "must": [
        #                     {
        #                         "match": {
        #                             "id_bibrec": pid.pid_value
        #                         }
        #                     },
        #                     {
        #                         "match": {
        #                             "_type": "events.cds_videos_pageviews"
        #                         }
        #                     }
        #                 ]
        #             }
        #         }
        #     }
        #     try:
        #         results = es.count(index=ES_INDEX, body=query).get('count', 0)
        #     except Exception:
        #         return make_response("Error getting statistics.", 400)

        # # Get timestamp-aggregated downloads for specific CDS record
        # elif stat == 'downloads':
        #     report_number = record.get('report_number')[0]
        #     key_type = 'date'
        #     query = {
        #         "query": {
        #             "filtered": {
        #                 "query": {
        #                     "bool": StatsResource._build_subquery(report_number)
        #                 },
        #                 "filter": {
        #                     "range": {
        #                         "@timestamp": {
        #                             "from": 0,
        #                             "to": "now"
        #                         }
        #                     }
        #                 }
        #             }
        #         },
        #         "aggregations": {
        #             "by_time": {
        #                 "date_histogram": {
        #                     "field": "@timestamp",
        #                     "interval": "day"
        #                 }
        #             }
        #         }
        #     }
        #     try:
        #         results = self.transform(
        #             es.search(index=ES_INDEX, body=query),
        #             stat,
        #             key_type)
        #     except Exception:
        #         return make_response("Error getting statistics.", 400)

        #     # Get timestamp-aggregated pageviews for specific CDS record
        # elif stat == 'pageviews':
        #     key_type = 'date'
        #     query = {
        #         "query": {
        #             "filtered": {
        #                 "query": {
        #                     "bool": {
        #                         "must": [
        #                             {
        #                                 "match": {
        #                                     "id_bibrec": pid.pid_value
        #                                 }
        #                             },
        #                             {
        #                                 "match": {
        #                                     "_type":
        #                                         "events.cds_videos_pageviews"
        #                                 }
        #                             }
        #                         ]
        #                     }
        #                 },
        #                 "filter": {
        #                     "range": {
        #                         "@timestamp": {
        #                             "from": 0,
        #                             "to": "now"
        #                         }
        #                     }
        #                 }
        #             }
        #         },
        #         "aggregations": {
        #             "by_time": {
        #                 "date_histogram": {
        #                     "field": "@timestamp",
        #                     "interval": "day"
        #                 }
        #             }
        #         }
        #     }
        #     try:
        #         results = self.transform(
        #             es.search(index=ES_INDEX, body=query),
        #             stat,
        #             key_type)
        #     except Exception:
        #         return make_response("Error getting statistics.", 400)

        from .api import Statistics

        # stats = Statistics.get_record_stats(recid=pid.pid_value)
        stats = Statistics.get_file_download_stats(file=record.get("report_number")[0])

        return make_response(jsonify(stats), 200)

    @pass_record
    @need_record_permission("read_permission_factory")
    def post(self, pid, record, **kwargs):
        """."""
        from flask import request, abort
        from invenio_files_rest.models import ObjectVersion

        data = request.get_json()
        event_name = data.get("event")
        bucket_id = record.get("_buckets", {}).get("record")

        if event_name == "record-view":
            cds_record_viewed.send(
                current_app._get_current_object(),
                pid=pid,
                record=record,
            )
            return make_response("", 202)
        elif event_name == "media-file-download":
            if "key" not in data:
                abort(406, "File key is required")
            if bucket_id is None:
                abort(406, "Record has no bucket")
            obj = ObjectVersion.get(bucket_id, data["key"])
            cds_record_media_downloaded.send(
                current_app._get_current_object(), obj=obj, record=record
            )
            return make_response("", 202)
        elif event_name == "media-record-view":
            if "key" not in data:
                abort(406, "File key is required")
            if bucket_id is None:
                abort(406, "Record has no bucket")
            obj = ObjectVersion.get(bucket_id, data["key"])
            cds_record_media_viewed.send(
                current_app._get_current_object(), obj=obj, record=record
            )
            return make_response("", 202)

        abort(500, "Invalid stats event request: {}".format(event_name))


blueprint.add_url_rule(
    '<pid(recid, record_class="cds.modules.records.api:CDSRecord"):pid_value>',
    view_func=StatsResource.as_view("record_stats"),
)
