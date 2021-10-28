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

import requests
from flask import current_app
from invenio_db import db
from invenio_files_rest.helpers import compute_md5_checksum
from invenio_files_rest.models import ObjectVersion, FileInstance,\
    ObjectVersionTag
from collections import defaultdict

from cds.modules.flows.models import TaskMetadata, Status
from celery import shared_task

from cds.modules.flows.tasks import TranscodeVideoTask
from cds.modules.opencast.error import MissingEventId
from cds.modules.xrootd.utils import file_opener_xrootd, file_size_xrootd


def _get_status_and_subformats(event_id, session):
    """Retrieves the status and the subformats of an event_id."""
    r = session.get(
        "{endpoint}/{event_id}?withpublications=true".format(
            endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_EVENTS'],
            event_id=event_id
        ),
        verify=False
    )
    json = r.json()
    status = json["processing_state"]
    publications = json["publications"]
    for publication in publications:
        if publication["channel"] == "api":
            subformats = publication["media"]
            break
    else:
        subformats = []  # TODO: to be changed
    return status, subformats


def _group_tasks_by_event_id(tasks):  # TODO: Create unit test
    """Group tasks by event_id."""
    groups = defaultdict(list)
    for obj in tasks:
        try:
            groups[obj.payload["opencast_event_id"]].append(obj)
        except KeyError:
            current_app.logger.error(
                'Opencast event id is missing in Task with id: {0} .'.format(
                    obj.id
                )
            )
    return groups.values()


def _write_file_to_eos(url_to_download, obj, session):
    """Stream file to eos."""
    file_instance = FileInstance.create()
    bucket_location = obj.bucket.location.uri
    storage = file_instance.storage(
        default_location=bucket_location)
    directory, filename = storage._get_fs()
    try:
        # XRootD Safe
        output_file = os.path.join(
            directory.root_url + directory.base_path, filename)
    except AttributeError:
        output_file = os.path.join(directory.root_path, filename)
    r = session.get(url_to_download, stream=True, verify=False)
    f = file_opener_xrootd(output_file, 'wb')
    for ch in r.iter_content(chunk_size=1000000):
        if ch:
            f.write(ch)
    f.close()
    with db.session.begin_nested():
        with file_opener_xrootd(output_file, 'rb') as transcoded_file:
            checksum = compute_md5_checksum(transcoded_file)
        size = file_size_xrootd(output_file)
        file_instance.set_uri(output_file, size, checksum)
        obj.set_file(file_instance)


@shared_task
def update_task_status():
    """Update all finished transcoding tasks."""
    # TODO: add ERROR HANDLING
    session = requests.Session()
    session.auth = (
        current_app.config['CDS_OPENCAST_API_USERNAME'],
        current_app.config['CDS_OPENCAST_API_PASSWORD']
    )
    pending_tasks = TaskMetadata.query.filter_by(
        status=Status.PENDING,
        name=TranscodeVideoTask().name
    ).all()
    grouped_tasks = _group_tasks_by_event_id(pending_tasks)
    print("--- Updating", len(pending_tasks))
    for tasks in grouped_tasks:
        print("Tasks: ", tasks)
        event_id = tasks[0].payload["opencast_event_id"]
        status, subformats = _get_status_and_subformats(event_id, session)
        master_object_version = ObjectVersion.get(
            bucket=tasks[0].payload["bucket_id"],
            key=tasks[0].payload["key"],
            version_id=tasks[0].payload["version_id"]
        )
        for task in tasks:
            for subformat in subformats:
                if task.payload[
                    "opencast_publication_tag"
                ] in subformat["tags"]:
                    update_task_success.delay(
                        str(task.id),
                        subformat["url"],
                        str(master_object_version.version_id),
                        event_id,
                        task.payload["quality"],
                    )
                elif status == "FAILED":
                    update_task_failure.delay(str(task.id))


@shared_task
def update_task_success(
        task_id, url, master_object_version_version_id, event_id, quality
):
    """Update Task status and files by streaming it to EOS."""
    # TODO: add ERROR HANDLING
    session = requests.Session()
    session.auth = (
        current_app.config['CDS_OPENCAST_API_USERNAME'],
        current_app.config['CDS_OPENCAST_API_PASSWORD']
    )
    task = TaskMetadata.query.get(task_id)
    obj = ObjectVersion.create(
        bucket=task.payload["bucket_id"],
        key=task.name
    )
    _write_file_to_eos(url, obj, session)
    ObjectVersionTag.create(
        obj, 'master', master_object_version_version_id
    )
    ObjectVersionTag.create(
        obj, '_opencast_event_id', event_id
    )
    ObjectVersionTag.create(obj, 'media_type', 'video')
    ObjectVersionTag.create(obj, 'context_type', 'subformat')
    ObjectVersionTag.create(obj, 'quality', quality)
    # TODO: maybe enrich a bit more the tags of the ObjectVersion
    task.status = Status.SUCCESS
    task.message = "Transcoding succeeded"
    task_payload = task.payload.copy()
    updated_payload = dict(
        key=obj.key, version_id=str(obj.version_id)
    )
    task_payload.update(**updated_payload)
    task.payload = task_payload
    db.session.commit()


@shared_task
def update_task_failure(task_id):
    """Update Task status to failed."""
    task = TaskMetadata.query.get(task_id)
    task.status = Status.FAILURE
    task.message = "Transcoding failed"
    db.session.commit()
