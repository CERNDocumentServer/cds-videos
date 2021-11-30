# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

from __future__ import absolute_import, print_function

import json

from flask import current_app, jsonify, url_for
from invenio_files_rest.models import as_object_version

from ..flows.models import FlowTaskStatus
from .tasks import DownloadTask, ExtractMetadataTask


def add_link_header(response, links):
    """Add a Link HTTP header to a REST response.

    :param response: REST response instance.
    :param links: Dictionary of links.
    """
    if links is not None:
        response.headers.extend(
            {
                "Link": ", ".join(
                    ['<{0}>; rel="{1}"'.format(l, r) for r, l in links.items()]
                )
            }
        )


def make_response(flow):
    """Make a response from flow object."""
    if not flow.is_last:
        code = 410
    else:
        code = FlowTaskStatus.status_to_http(flow.status)

    response = {}
    response.update(flow_response_links(flow))
    response.update(serialize_flow_tasks(flow))

    presets = list(current_app.config["CDS_OPENCAST_QUALITIES"].keys())
    response.update(
        {
            "flow_status": str(flow.status),
            "presets": presets,
            "deposit_id": flow.deposit_id,
        }
    )
    response = jsonify(response)
    response.headers["X-Hub-Delivery"] = flow.id
    add_link_header(
        response,
        {"self": url_for(".flow_item", flow_id=flow.id, _external=True)},
    )
    return response, code


def flow_response_links(flow):
    version_id = flow.payload["version_id"]
    object_version = as_object_version(version_id)
    obj_tags = object_version.get_tags()
    obj_key = object_version.key
    obj_bucket_id = str(object_version.bucket_id)
    return dict(
        links={
            "self": url_for(
                "invenio_files_rest.object_api",
                bucket_id=obj_bucket_id,
                key=obj_key,
                _external=True,
            ),
            "cancel": url_for(
                "cds_flows.flow_item",
                flow_id=flow.id,
                _external=True,
            ),
        },
        key=obj_key,
        version_id=version_id,
        tags=obj_tags,
    )


def serialize_flow_tasks(flow):
    return dict(_tasks=get_flow_tasks_statuses(flow.to_dict()))


def get_flow_tasks_statuses(flow_dict):
    """Build the list of Tasks statuses."""
    first_group = []
    second_group = []

    for task in flow_dict["tasks"]:
        task_status = get_flow_task_statuses(task)

        task_name = task_status["name"]
        # Calculate the right position inside the tuple
        # download and extract metadata comes first
        group = (
            first_group
            if task_name in (DownloadTask.name, ExtractMetadataTask.name)
            else second_group
        )

        group.append(task_status)

    second_group = sorted(
        second_group, key=lambda s: s["info"]["payload"]["order"]
    )
    return first_group, second_group


def get_flow_task_statuses(task_dict):
    """Serialize the task status."""
    task_name = task_dict["name"]

    # Add the payload information
    payload = task_dict["payload"]
    payload["type"] = task_name
    payload["key"] = payload.get("preset_quality", payload["key"])

    # try to cast the preset quality key to an int to then sort the list of
    # qualities, getting only the numbers from the key. '360p' -> 360
    only_digits = "".join(filter(str.isdigit, str(payload["key"]))) or 0
    payload["order"] = int(only_digits)

    if task_name == ExtractMetadataTask.name:
        # try to return the msg as JSON, given that it contains some form
        # fields to enable auto-filling.
        # we only need this for this particular task
        try:
            payload["extracted_metadata"] = json.loads(task_dict["message"])
        except ValueError:
            payload["extracted_metadata"] = task_dict["message"]

    task_status = {
        "name": task_name,
        "id": task_dict["id"],
        "status": task_dict["status"],
        "info": {
            "payload": payload,
            "message": task_dict["message"],
        },
    }

    return task_status


def serialize_flow(flow):
    """Get the serialized flow status."""
    response_code = FlowTaskStatus.status_to_http(flow.status)
    if not flow.is_last:
        # in case the flow has been replaced
        # return what was already in the response
        return 410

    flow_dict = flow.to_dict()

    if "tasks" in flow_dict:
        # Extract info and build correct status dict
        flow_dict = get_flow_tasks_statuses(flow_dict)
    return response_code, flow_dict
