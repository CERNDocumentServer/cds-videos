# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2021 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.
"""Celery tasks for Opencast."""

import os
import signal
import time
from collections import defaultdict

import requests
from celery import current_app as celery_app
from celery import shared_task
from flask import current_app
from invenio_cache import current_cache
from invenio_db import db
from invenio_files_rest.helpers import compute_md5_checksum
from invenio_files_rest.models import (FileInstance, ObjectVersion,
                                       ObjectVersionTag, as_object_version,
                                       as_bucket)
from invenio_pidstore.errors import PIDDeletedError, PIDDoesNotExistError

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.flows.decorators import retry
from cds.modules.flows.deposit import index_deposit_project
from cds.modules.flows.models import FlowTaskMetadata
from cds.modules.flows.models import FlowTaskStatus as FlowTaskStatus
from cds.modules.flows.tasks import (TranscodeVideoTask,
                                     sync_records_with_deposit_files)
from cds.modules.opencast.api import OpenCastRequestSession
from cds.modules.opencast.error import (AbruptCeleryStop, RequestError,
                                        WriteToEOSError, RequestError404)
from cds.modules.opencast.utils import generate_lock_id, only_one
from cds.modules.records.utils import to_string
from cds.modules.xrootd.utils import file_opener_xrootd, file_size_xrootd


@retry(sleep=2, max_retries=5, exception=RequestError404)
def _get_status_and_subformats(event_id, session):
    """Retrieves the status and the subformats of an event_id."""
    url = "{endpoint}/{event_id}?withpublications=true".format(
        endpoint="{host}/api/events".format(
            host=current_app.config["CDS_OPENCAST_HOST"]
        ),
        event_id=event_id,
    )
    try:
        response = session.get(
            url,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise RequestError404(url, e)
    except requests.exceptions.RequestException as e:
        raise RequestError(url, e)

    json = response.json()
    status = json["processing_state"]
    publications = json.get("publications", [])
    for publication in publications:
        if publication["channel"] == "api":
            subformats = publication["media"]
            break
    else:
        # no `break`
        subformats = []
    return status, subformats


def _update_task_on_abrupt_stop(flow_task, opencast_event_id):
    """Update task on abrupt stop and raise an exception."""
    # Releasing lock
    cache = current_cache.cache
    lock_id = generate_lock_id(str(flow_task.id), opencast_event_id)
    if cache.has(lock_id):
        current_app.logger.info(
            "Releasing lock with id: {0}".format(lock_id)
        )
        cache.delete(lock_id)

    # Update tasks status
    error_message = "Abrupt celery stop"
    current_app.logger.error(error_message)
    flow_task.status = FlowTaskStatus.FAILURE
    flow_task.message = error_message
    db.session.commit()
    raise AbruptCeleryStop(task_id=str(flow_task.id))


def _group_tasks_by_opencast_event_id(tasks):
    """Group tasks by event_id."""
    groups = defaultdict(list)
    for obj in tasks:
        try:
            event_id = obj.payload["opencast_event_id"]
            groups[event_id].append(obj)
        except KeyError:
            current_app.logger.error(
                "Opencast event id is missing in Task with id: {0} .".format(
                    obj.id
                )
            )
    return groups.values()


def get_opencast_events(grouped_flow_tasks):
    """Get OpenCast events responses for given Flow Tasks."""
    opencast_events = dict()

    session_context = OpenCastRequestSession(
        current_app.config["CDS_OPENCAST_API_USERNAME"],
        current_app.config["CDS_OPENCAST_API_PASSWORD"],
        current_app.config["CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT"],
    )
    with session_context as session:
        for started_flow_tasks in grouped_flow_tasks:
            # the opencast event id is the same for all transcoding tasks
            event_id = started_flow_tasks[0].payload["opencast_event_id"]
            try:
                (
                    opencast_workflow_status,
                    opencast_published_subformats,
                ) = _get_status_and_subformats(event_id, session)

                opencast_events[event_id] = dict(
                    status=opencast_workflow_status,
                    subformats=opencast_published_subformats,
                )
            except RequestError as e:
                msg = (
                    "Failed to fetch status and subformats from Opencast "
                    "event id: {0}. Request failed on: {1}. "
                    "Error message: {2}".format(
                        event_id,
                        e.url,
                        e.message,
                    )
                )
                flow_task_ids_with_error = [
                    (str(flow_task.id), msg)
                    for flow_task in started_flow_tasks
                ]
                _set_flow_tasks_to_failed(flow_task_ids_with_error)
                current_app.logger.error(msg)
                continue

    return opencast_events


@shared_task
@only_one(
    key="check_transcoding_status",
    timeout_config_name="CDS_OPENCAST_STATUS_CHECK_TASK_TIMEOUT"
)
def check_transcoding_status():
    """Update all finished transcoding tasks."""
    number_of_transcoding_tasks_started = 0
    started_transcoding_tasks = FlowTaskMetadata.query.filter_by(
        status=FlowTaskStatus.STARTED, name=TranscodeVideoTask.name
    ).all()
    grouped_flow_tasks = _group_tasks_by_opencast_event_id(
        started_transcoding_tasks
    )

    if not grouped_flow_tasks:
        # nothing to do
        current_app.logger.debug(
            "No started transcoding tasks to check, exiting"
        )
        return

    opencast_events = get_opencast_events(grouped_flow_tasks)

    if started_transcoding_tasks:
        current_app.logger.debug(
            "Triggering status check for {0} transcoding task".format(
                len(started_transcoding_tasks)
            )
        )
    for started_flow_tasks in grouped_flow_tasks:

        # the opencast event id is the same for all transcoding tasks
        event_id = started_flow_tasks[0].payload["opencast_event_id"]
        opencast_event = opencast_events.get(event_id)
        if not opencast_event:
            continue

        for started_flow_task in started_flow_tasks:
            for subformat in opencast_event["subformats"]:
                is_same_preset_quality = (
                    started_flow_task.payload["opencast_publication_tag"]
                    in subformat["tags"]
                )
                if not is_same_preset_quality:
                    continue

                on_transcoding_completed.s(
                    flow_task_id=str(started_flow_task.id),
                    opencast_subformat=subformat,
                    opencast_event_id=event_id
                ).apply_async(
                    link_error=on_celery_task_failed.s(
                        data=dict(flow_task_id=str(started_flow_task.id))
                    ),
                )
                number_of_transcoding_tasks_started += 1
                # transcoding subformat completed, `break` to go to the next
                break
            else:
                # no `break`, the transcoded subformat might not yet
                # ready, or if workflow failed, this subformat failed
                if opencast_event["status"] == "FAILED":
                    msg = (
                        "Opencast event 'processing_state' field has "
                        "value 'FAILED' for event id: {0}.".format(event_id)
                    )
                    _set_flow_tasks_to_failed(
                        [(str(started_flow_task.id), msg)]
                    )
    if number_of_transcoding_tasks_started:
        current_app.logger.debug(
            "Started {0} on_transcoding_completed tasks".format(
                number_of_transcoding_tasks_started
            )
        )
    else:
        current_app.logger.debug(
            "No on_transcoding_completed tasks started"
        )


def _get_opencast_subformat_info(subformat, present_quality):
    """Get subformat info merging default config when missing."""
    default_config = current_app.config["CDS_OPENCAST_QUALITIES"][
        present_quality
    ]
    info = dict(
        frame_rate=int(subformat.get("framerate", default_config["frame_rate"])),
        height=int(subformat.get("height", default_config["height"])),
        width=int(subformat.get("width", default_config["width"])),
        video_bitrate=int(subformat.get(
            "bitrate",  # this is the video bitrate
            default_config["video_bitrate"],
        )),
    )
    return info


def _write_file_to_eos(url_to_download, obj):
    """Stream file to eos."""
    file_instance = FileInstance.create()
    bucket_location = obj.bucket.location.uri
    storage = file_instance.storage(default_location=bucket_location)
    directory, filename = storage._get_fs()
    start = time.time()
    try:
        # XRootD Safe
        file_uri = os.path.join(
            directory.root_url + directory.base_path, filename
        )
    except AttributeError:
        file_uri = os.path.join(directory.root_path, filename)

    session_context = OpenCastRequestSession(
        current_app.config["CDS_OPENCAST_API_USERNAME"],
        current_app.config["CDS_OPENCAST_API_PASSWORD"],
        current_app.config["CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT"],
    )
    with session_context as session:
        r = session.get(
            url_to_download,
            stream=True,
            verify=current_app.config["CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT"],
        )
        f = file_opener_xrootd(file_uri, "wb")
        for ch in r.iter_content(chunk_size=1024*1024):
            if ch:
                f.write(ch)
        f.close()
    end = time.time()

    size = file_size_xrootd(file_uri)
    with db.session.begin_nested():
        with file_opener_xrootd(file_uri, "rb") as transcoded_file:
            checksum = compute_md5_checksum(transcoded_file)
        file_instance.set_uri(file_uri, size, checksum)
        obj.set_file(file_instance)

    return int(end - start), size * 0.000001


def set_revoke_handler(handler):
    """Set handler to be executed when the task gets revoked."""

    def _handler(signum, frame):
        with celery_app.flask_app.app_context():
            handler()

    signal.signal(signal.SIGTERM, _handler)


@shared_task
@only_one(
    timeout_config_name="CDS_OPENCAST_DOWNLOAD_TASK_TIMEOUT",
    use_kwargs_as_key=True
)
def on_transcoding_completed(
        flow_task_id=None,
        opencast_subformat=None,
        opencast_event_id=None
):
    """Update Task status and files by streaming it to EOS.

    :param flow_task_id: Task id.
    :param opencast_subformat: Subformat dict.
    :param opencast_event_id: Opencast event ID.

    WARNING: Do not remove opencast_event_id and flow_task_id, needed for
     @only_one decorator
    """
    flow_task = FlowTaskMetadata.query.get(flow_task_id)
    if not flow_task:
        return
    set_revoke_handler(
        lambda: _update_task_on_abrupt_stop(flow_task, opencast_event_id)
    )
    preset_quality = flow_task.payload["preset_quality"]
    master_object_version = as_object_version(
        flow_task.payload["master_id"]
    )
    master_object_version_id = str(master_object_version.version_id)

    deposit_id = flow_task.payload["deposit_id"]
    try:
        deposit_video = deposit_video_resolver(deposit_id)
    except PIDDeletedError:
        # If the video was soft deleted we still process the tasks
        # If bucket is locked, we unlock and lock it again before exiting
        deposit_video = None
        bucket = as_bucket(flow_task.payload["bucket_id"])
        bucket_was_locked = bucket.locked
        if bucket_was_locked:
            bucket.locked = False
        pass
    except PIDDoesNotExistError:
        # If video was hard deleted just exit
        return

    if deposit_video:
        deposit_video_is_published = deposit_video.is_published()
        if deposit_video_is_published:
            assert deposit_video.files.bucket.locked
            deposit_video.files.bucket.locked = False

    obj = ObjectVersion.create(
        bucket=flow_task.payload["bucket_id"],
        key="{0}.mp4".format(flow_task.payload["preset_quality"]),
    )

    download_url = opencast_subformat["url"]
    try:
        download_time, file_size = _write_file_to_eos(download_url, obj)
    except Exception as e:
        error_message = (
            "Failed to write transcoded file to EOS. Request "
            "failed on: {0}. Error: {1}"
        ).format(download_url, str(e))
        current_app.logger.error(error_message)
        flow_task.status = FlowTaskStatus.FAILURE
        flow_task.message = error_message
        db.session.expunge(obj)  # Remove object_version from session
        db.session.commit()
        raise WriteToEOSError(download_url, str(e))

    # Check if status changed while downloading and if so don't update
    db.session.refresh(flow_task)
    status = flow_task.status
    if status != FlowTaskStatus.STARTED:
        current_app.logger.error("Task status has changed while the "
                                 "file was being written to EOS. Aborting task"
                                 "update. Task ID: {0}".format(flow_task_id))
        db.session.expunge(obj)  # Remove object_version from session
        return

    # add various tags to the subformat
    ObjectVersionTag.create(obj, "master", master_object_version_id)
    ObjectVersionTag.create(obj, "_opencast_event_id", opencast_event_id)
    ObjectVersionTag.create(obj, "media_type", "video")
    ObjectVersionTag.create(obj, "context_type", "subformat")
    ObjectVersionTag.create(obj, "smil", "true")
    ObjectVersionTag.create(obj, "preset_quality", preset_quality)
    ObjectVersionTag.create(
        obj, "_opencast_file_download_time_in_seconds", str(download_time)
    )
    qualitiy_config = current_app.config["CDS_OPENCAST_QUALITIES"][
        preset_quality
    ]
    if "tags" in qualitiy_config:
        for key, value in qualitiy_config["tags"].items():
            ObjectVersionTag.create(obj, key, value)
    # add tags extracted from the subformat info
    info = _get_opencast_subformat_info(opencast_subformat, preset_quality)
    for key, value in info.items():
        ObjectVersionTag.create(obj, key, to_string(value))

    flow_task.status = FlowTaskStatus.SUCCESS
    flow_task.message = "Transcoding succeeded"

    # JSONb cols needs to be assigned (not updated) to be persisted
    new_payload = dict(flow_task.payload)
    new_payload.update(
        key=obj.key,
        version_id=str(obj.version_id),
        opencast_file_download_time_in_seconds=str(download_time),
        file_size_mb=str(file_size),
    )
    flow_task.payload = new_payload

    if deposit_video:
        if deposit_video_is_published:
            sync_records_with_deposit_files(deposit_id)
            deposit_video.files.bucket.locked = True
        index_deposit_project(deposit_id)
    else:
        if bucket_was_locked:
            bucket.locked = True

    db.session.commit()


@shared_task
def on_celery_task_failed(request, exc, traceback, data, **kwargs):
    """On task failed."""
    current_app.logger.error(repr(exc))
    flow_task_id = data["flow_task_id"]
    _set_flow_tasks_to_failed([(flow_task_id, repr(exc))])


def _set_flow_tasks_to_failed(flow_tasks_ids_with_error):
    """Set the given Flow Task to failed."""
    for id_, error in flow_tasks_ids_with_error:
        flow_task = FlowTaskMetadata.query.get(id_)
        flow_task.status = FlowTaskStatus.FAILURE
        flow_task.message = error

        db.session.commit()
        try:
            index_deposit_project(flow_task.payload["deposit_id"])
        except PIDDeletedError:
            pass
