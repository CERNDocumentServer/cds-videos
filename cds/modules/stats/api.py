# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 TU Wien.
#
# Invenio RDM Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Permission factories for Invenio-Stats.

In contrast to the very liberal defaults provided by Invenio-Stats, these permission
factories deny access unless otherwise specified.
"""

from flask import current_app
from invenio_stats.proxies import current_stats


class Statistics:
    """Statistics API class."""

    @classmethod
    def _get_query(cls, query_name):
        """Build the statistics query from configuration."""
        query_config = current_stats.queries[query_name]
        return query_config.cls(name=query_config.name, **query_config.params)

    @classmethod
    def get_record_stats(cls, recid):
        """Fetch the statistics for the given record."""
        try:
            views = cls._get_query("record-view-total").run(recid=recid)
        except Exception as e:
            # e.g. opensearchpy.exceptions.NotFoundError
            # when the aggregation search index hasn't been created yet
            current_app.logger.warning(e)

            fallback_result = {"views": 0, "unique_views": 0}
            views = fallback_result

        stats = {
            "views": views["views"],
            "unique_views": views["unique_views"],
        }
        return stats

    @classmethod
    def get_file_download_stats(cls, file):
        """Fetch the statistics for the given record."""
        try:
            views = cls._get_query("file-download-total").run(file=file)
        except Exception as e:
            # e.g. opensearchpy.exceptions.NotFoundError
            # when the aggregation search index hasn't been created yet
            current_app.logger.warning(e)

            fallback_result = {"views": 0, "unique_views": 0}
            views = fallback_result

        stats = {
            "views": views["views"],
            "unique_views": views["unique_views"],
        }
        return stats
