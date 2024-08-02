# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 TU Wien.
#
# Invenio RDM Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Custom event builders for the CDS Videos statistics."""

import datetime
from os.path import splitext

from invenio_search.engine import dsl
from invenio_stats.utils import get_user


def file_download_event_builder(event, sender_app, obj=None, record=None, **kwargs):
    """Build a file-download event."""
    tags = obj.get_tags()
    # File information
    content_type = splitext(obj.key)[1][1:].lower()
    tags = obj.get_tags()
    context_type = tags.pop("context_type", "")
    if context_type == "master":
        quality = "master"
    elif context_type == "subformat":
        quality = tags.get("preset_quality")
    else:
        quality = "frame"
    media_type = tags.pop("media_type", "")
    report_number = record.get("report_number", [""])[0]

    event.update(
        {
            # When:
            "timestamp": datetime.datetime.utcnow().isoformat(),
            # What:
            "format": content_type,
            "type": media_type,
            "quality": quality,
            # Used only for unique id
            "bucket_id": str(obj.bucket_id),
            "file_id": str(obj.file_id),
            # we log the reportnumber as file key to make sure that the filename
            # matches the record report number
            "file": report_number,
            # Who:
            **get_user(),
        }
    )
    return event


def media_record_view_event_builder(event, sender_app, obj=None, record=None, **kwargs):
    """Build a media record view event.

    This is the event tracking users clicking the play button on videos.
    """
    tags = obj.get_tags()
    # File information
    content_type = splitext(obj.key)[1][1:].lower()
    tags = obj.get_tags()
    media_type = tags.pop("media_type", "")
    report_number = record.get("report_number", [""])[0]
    recid = record.get("recid")

    event.update(
        {
            # When:
            "timestamp": datetime.datetime.utcnow().isoformat(),
            # What:
            "recid": str(recid),
            "format": content_type,
            "type": media_type,
            # Used only for unique id
            "bucket_id": str(obj.bucket_id),
            "file_id": str(obj.file_id),
            # we log the reportnumber as file key to make sure that the filename
            # matches the record report number
            "file": report_number,
            # Who:
            **get_user(),
        }
    )
    return event


def record_view_event_builder(event, sender_app, pid=None, record=None, **kwargs):
    """Build a record-view event."""
    # TODO: does it make sense for other pid types?
    if pid.pid_type != "recid":
        return
    event.update(
        {
            # When:
            "timestamp": datetime.datetime.utcnow().isoformat(),
            # What:
            "record_id": str(record.id),
            "pid_type": pid.pid_type,
            "pid_value": str(pid.pid_value),
            # Who:
            **get_user(),
        }
    )
    return event


def build_file_unique_id(doc):
    """Build file unique identifier."""
    doc["unique_id"] = "{0}_{1}".format(
        doc.pop("bucket_id", ""), doc.pop("file_id", "")
    )
    return doc


def build_record_unique_id(doc):
    """Build record unique identifier."""
    doc["unique_id"] = "{0}_{1}".format(doc["pid_type"], doc["pid_value"])
    return doc


def drop_undesired_fields(doc):
    """Flag events which are created by robots.

    The list of robots is defined by the `COUNTER-robots Python package
    <https://github.com/inveniosoftware/counter-robots>`_ , which follows the
    `list defined by Project COUNTER
    <https://www.projectcounter.org/appendices/850-2/>`_ that was later split
    into robots and machines by `the Make Data Count project
    <https://github.com/CDLUC3/Make-Data-Count/tree/master/user-agents>`_.
    """
    doc.pop("country", None)
    doc.pop("referrer", None)
    return doc


def filter_by_reportnumber(query, **kwargs):
    """OpenSearch subquery for download statistics.
    Because the report number was changed for consistency reasons,
    we had to build a workaround so that we can target old videos
    by report number.

    :param report_number: the report number of a record
    """
    report_number = kwargs.get("file")

    if "VIDEO" in report_number:
        report_number_movie = report_number.replace("VIDEO", "MOVIE")
        report_number_videoclip = report_number.replace("VIDEO", "VIDEOCLIP")
        q = dsl.query.Bool(
            "should",
            should=[
                dsl.dsl.Q("term", **{"file": report_number}),
                dsl.dsl.Q("term", **{"file": report_number_movie}),
                dsl.dsl.Q("term", **{"file": report_number_videoclip}),
            ],
            minimum_should_match=1,
        )
        query = query.filter(q)
    if "FOOTAGE" in report_number:
        report_number_videorush = report_number.replace("FOOTAGE", "VIDEORUSH")
        q = dsl.query.Bool(
            "should",
            should=[
                dsl.dsl.Q("term", **{"file": report_number}),
                dsl.dsl.Q("term", **{"file": report_number_videorush}),
            ],
            minimum_should_match=1,
        )
        query = query.filter(q)
    return query
