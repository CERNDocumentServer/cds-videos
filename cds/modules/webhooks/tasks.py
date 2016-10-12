# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""Celery tasks for Webhook Receivers."""

from __future__ import absolute_import, division

import json
import requests
import signal
import time
from math import ceil
from os import listdir, rename
from os.path import isfile, join
from PIL import Image

from cds.modules.webhooks.task_classes import with_order, AVCOrchestrator
from six import BytesIO

from cds.modules.ffmpeg import ff_frames, ff_probe, ff_probe_all
from cds_sorenson.api import get_encoding_status, start_encoding, stop_encoding
from celery import chain, group, shared_task
from flask import current_app as flask_app
from invenio_db import db
from invenio_files_rest.models import MultipartObject, ObjectVersion, Part


@shared_task(bind=True, base=with_order(1))
def download(self, url, bucket_id, chunk_size, key=None):
    """Download file from a URL.

    :param url: URL of the file to download.
    :param bucket_id: ID of the bucket where the file will be stored.
    :param chunk_size: Size of the chunks for downloading.
    :param parent_id: ID of the parent task.
    :param key: New filename. If not provided, the filename will be taken from
                the URL.
    """
    if self.parent:
        self.parent.clear_state()

    # Make HTTP request
    response = requests.get(url, stream=True)
    total = int(response.headers.get('Content-Length'))
    if not key:
        key = url.rsplit('/', 1)[-1]

    # Stream data into bucket's object
    self.update_progress(0)
    if total is None or total < chunk_size:
        mp = ObjectVersion.create(bucket_id, key,
                                  stream=BytesIO(response.content))
    else:
        cur = 0
        part_cnt = 0
        mp = MultipartObject.create(bucket_id, key, total, chunk_size)

        for chunk in response.iter_content(chunk_size=chunk_size):
            cur += len(chunk)
            Part.create(mp, part_cnt, BytesIO(chunk))
            part_cnt += 1
            self.update_progress_with_size(cur, total)
        mp.complete()
        mp.merge_parts()
    self.update_progress(100)

    # Get downloaded file location
    file_location = mp.file.uri
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return file_location


@shared_task(bind=True, base=with_order(2))
def transcode(self, input_filename, preset_name):
    """Transcode video on Sorenson."""
    self.update_progress(0)

    # Start encoding on Sorenson server
    job_id = start_encoding(input_filename, preset_name)

    # Set handler for canceling task
    def handler(signum, frame):
        stop_encoding(job_id)
    signal.signal(signal.SIGTERM, handler)

    # Query Sorenson for job status every second
    response = get_encoding_status(job_id)
    while response['Status']['TimeFinished'] is None:
        percentage = response['Status']['Progress']
        self.update_progress(percentage)
        response = get_encoding_status(job_id)
        time.sleep(1)

    self.update_progress(100)
    return flask_app.config['CDS_SORENSON_OUTPUT_FOLDER']


@shared_task(bind=True, base=with_order(2))
def extract_frames(self, input_filename, start_percentage, end_percentage,
                   number_of_frames, size_percentage, output_folder):
    """Extract thumbnails for some frames of the video."""
    # Extract video information
    output = join(output_folder, 'img%d.jpg')
    duration = float(ff_probe(input_filename, 'duration'))
    width = int(ff_probe(input_filename, 'width'))
    height = int(ff_probe(input_filename, 'height'))
    size_percentage /= 100
    thumbnail_size = (width * size_percentage, height * size_percentage)
    step_percent = (end_percentage - start_percentage) / (number_of_frames - 1)

    # Calculate time step
    start_time = int(duration * start_percentage / 100)
    end_time = ceil(duration * end_percentage / 100)
    time_step = int(duration * step_percent / 100)

    # Extract all requested frames as thumbnail images (full resolution)
    self.update_progress(0)
    for seconds in ff_frames(input_filename, start_time, end_time,
                             time_step, output):
        self.update_progress_with_size(seconds, duration)

    # Resize thumbnails to requested dimensions
    for i in range(number_of_frames):
        filename = join(output_folder, 'img{}.jpg'.format(i + 1))
        im = Image.open(filename)
        im.thumbnail(thumbnail_size)
        im.save(filename)

        percentage = int(start_percentage + i * step_percent)
        new_filename = 'thumbnail-{0}x{1}-at-{2}-percent.jpg'.format(
            int(thumbnail_size[0]), int(thumbnail_size[1]), percentage
        )
        rename(filename, join(output_folder, new_filename))
    self.update_progress(100)

    return output_folder


@shared_task(bind=True, base=with_order(3))
def attach_files(self, output_folders, bucket_id, key):
    """Create records from Sorenson's generated subformats."""
    # Collect
    files = [join(output_folder, filename)
             for output_folder in output_folders
             for filename in listdir(output_folder)
             if isfile(join(output_folder, filename))]

    # Attach
    total = len(files)

    for count, filename in enumerate(files):
        ObjectVersion.create(bucket_id, key, stream=open(filename, 'rb'))
        self.update_progress_with_size(count + 1, total)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


@shared_task(bind=True, base=AVCOrchestrator)
def chain_orchestrator(self, workflow, **kwargs):
    """Orchestration task for chained Celery tasks or groups of tasks."""

    task_list = []
    parent_kw = {'parent': self}
    for task_definition in workflow:
        if isinstance(task_definition, tuple):
            task, task_kw = task_definition
            kw = {k: kwargs[k] for k in kwargs if k in task_kw}
            kw.update(parent_kw)
            task_list.append(task.subtask(kwargs=kw))
        elif isinstance(task_definition, list):
            subtasks = []
            for task, task_kw in task_definition:
                kw = {k: kwargs[k] for k in kwargs if k in task_kw}
                kw.update(parent_kw)
                subtasks.append(task.subtask(kwargs=kw))
            task_list.append(group(*subtasks))
    return chain(*task_list)().id


@shared_task()
def extract_metadata(video_location):
    """Extract metadata from given video file."""
    information = json.loads(ff_probe_all(video_location))
    return information  # TODO output to file?
