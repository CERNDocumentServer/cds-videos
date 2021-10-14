from __future__ import absolute_import, print_function

from cds_sorenson.api import get_all_distinct_qualities
from invenio_files_rest.models import (
    as_object_version,
)
from flask import url_for, jsonify

from ..flows.models import Status as FlowStatus

from .task_api import Task


def add_link_header(response, links):
    """Add a Link HTTP header to a REST response.

    :param response: REST response instance.
    :param links: Dictionary of links.
    """
    if links is not None:
        response.headers.extend({
            'Link': ', '.join([
                '<{0}>; rel="{1}"'.format(l, r) for r, l in links.items()])
        })


def make_response(flow):
    """Make a response from flow object."""
    code = FlowStatus.status_to_http(flow.status)

    response = {}
    response.update(flow_response_links(flow))
    response.update(serialize_flow_tasks(flow))
    response.update({
        "global_status": str(flow.status),
        "presets": get_all_distinct_qualities()
                     })
    response.update("")

    response = jsonify(response)
    response.headers['X-Hub-Delivery'] = flow.id
    add_link_header(response, {'self': url_for(
        '.flow_item', flow_id=flow.id,
        _external=True
    )})
    return response, code


def flow_response_links(flow):
    version_id = flow.payload['version_id']
    object_version = as_object_version(version_id)
    obj_tags = object_version.get_tags()
    obj_key = object_version.key
    obj_bucket_id = str(object_version.bucket_id)
    return dict(
        links={
            'self': url_for(
                'invenio_files_rest.object_api',
                bucket_id=obj_bucket_id,
                key=obj_key,
                _external=True,
            ),
            'cancel': url_for(
                'cds_webhooks.flow_item',
                flow_id=flow.id,
                _external=True,
            ),
        },
        key=obj_key,
        version_id=version_id,
        tags=obj_tags,
    )


def serialize_flow_tasks(flow):
    return dict(
        _tasks=build_flow_status_json(flow.json)
    )


def build_flow_status_json(flow_json):
    """Build serialized status object."""
    status = ([], [])
    for task in flow_json['tasks']:
        task_status = Task.build_task_json_status(task)

        # Get the UI name of the task
        task_name = task_status["name"]
        assert task_name
        # Calculate the right position inside the tuple
        step = (
            0
            if task_name
            in ('file_download', 'file_video_metadata_extraction')
            else 1
        )

        status[step].append(task_status)

    return status


def serialize_flow(flow):
    """Get the serialized flow status."""
    response_code = FlowStatus.status_to_http(flow.status)
    if flow.deleted:
        # in case the flow has been removed
        # return what was already in the response
        return 410

    full_json = flow.json

    if 'tasks' in full_json:
        # Extract info and build correct status dict
        full_json = build_flow_status_json(full_json)
    return response_code, full_json
