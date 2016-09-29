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

from math import ceil

from cds.modules.webhooks.ffmpeg import ff_frames, ff_probe, ff_probe_all
from celery.task import Task

from os import listdir, rename
from os.path import join, isfile
import requests
import signal
import time
import json

from PIL import Image
from celery import current_task, shared_task
from celery.result import AsyncResult
from celery.states import state
from celery._state import current_app
from cds_sorenson.api import get_encoding_status, start_encoding, stop_encoding

from invenio_db import db
from invenio_files_rest.models import ObjectVersion, MultipartObject, Part
from six import BytesIO, b


class FailureBaseTask(Task):
    """Base class for tasks that propagate exceptions to a state's metadata."""
    def run(self, *args, **kwargs):
        """Identical run method."""
        self.run(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Gracefully handle task exceptions."""
        self.update_state(
            state='EXCEPTION',
            meta={'message': str(einfo.exception)}
        )


def clear_progress(task_id):
    """Delete all progress entries from state."""
    result = AsyncResult(task_id)
    progresses = result.info.get('progresses', {}) if result.info else {}
    progresses.clear()
    current_app.backend.store_result(
        task_id,
        dict(progresses=progresses),
        state('STARTED')
    )


def progress_updater_with_size(size, total, task_id):
    """Report progress of downloading celery task."""
    progress_updater(size/total * 100, task_id)


def progress_updater(percentage, task_id):
    """Report progress of downloading celery task."""

    # Get current task progresses
    result = AsyncResult(task_id)
    progresses = result.info.get('progresses', {}) if result.info else {}

    # Create/update progress for current task
    progresses[_extract_task_name()] = percentage

    # Update state
    current_app.backend.store_result(
        task_id,
        dict(progresses=progresses),
        state('PROGRESS')
    )


@shared_task(base=FailureBaseTask)
def extract_metadata(video_location):
    """Extract metadata from given video file."""
    information = json.loads(ff_probe_all(video_location))
    print(information)  # TODO output to file?


@shared_task(base=FailureBaseTask)
def download(url, bucket_id, key, chunk_size, parent_id):
    """Download file from a URL."""

    clear_progress(parent_id)
    response = requests.get(url, stream=True)
    total = int(response.headers.get('Content-Length'))

    if total is None or total < chunk_size:
        mp = ObjectVersion.create(bucket_id, key,
                                  stream=BytesIO(b(response.content)))
    else:
        cur = 0
        part_cnt = 0
        mp = MultipartObject.create(bucket_id, key, total, chunk_size)

        progress_updater(0, parent_id)
        for chunk in response.iter_content(chunk_size=chunk_size):
            cur += len(chunk)
            Part.create(mp, part_cnt, BytesIO(b(chunk)))
            part_cnt += 1
            progress_updater_with_size(cur, total, parent_id)
        mp.complete()
        mp.merge_parts()
    progress_updater(100, parent_id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return mp.file.uri


@shared_task(base=FailureBaseTask)
def transcode(input_filename, preset_name, parent_id):
    """Transcode video on Sorenson."""

    from ...wsgi import application
    api_app = application.wsgi_app.mounts['/api']  # FIXME elegant solution
    with api_app.app_context():

        job_id = start_encoding(input_filename, preset_name)

        def handler(signum, frame):
            stop_encoding(job_id)
        signal.signal(signal.SIGTERM, handler)

        response = get_encoding_status(job_id)
        while response['Status']['TimeFinished'] is None:
            percentage = response['Status']['Progress']
            progress_updater(percentage, parent_id)
            response = get_encoding_status(job_id)
            time.sleep(1)
    progress_updater(100, parent_id)
    return api_app.config['CDS_SORENSON_OUTPUT_FOLDER']


@shared_task(base=FailureBaseTask)
def extract_frames(input_filename, start_percentage, end_percentage,
                   number_of_frames, size_percentage, output_folder,
                   parent_id):
    """Extract thumbnails for some frames of the video."""

    # Extract video information
    output = join(output_folder, 'img%d.jpg')
    duration = float(ff_probe(input_filename, 'duration'))
    width = int(ff_probe(input_filename, 'width'))
    height = int(ff_probe(input_filename, 'height'))
    size_percentage = _percent_to_real(size_percentage)
    thumbnail_size = (width * size_percentage, height * size_percentage)
    step_percent = (end_percentage - start_percentage) / (number_of_frames - 1)

    # Calculate time step
    start_time = int(duration * _percent_to_real(start_percentage))
    end_time = ceil(duration * _percent_to_real(end_percentage))
    time_step = int(duration * _percent_to_real(step_percent))

    # Extract all requested frames as thumbnail images (full resolution)
    progress_updater(0, parent_id)
    for seconds in ff_frames(input_filename, start_time, end_time,
                             time_step, output):
        progress_updater_with_size(seconds, duration, parent_id)

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
    progress_updater(100, parent_id)

    return output_folder


@shared_task(base=FailureBaseTask)
def attach_files(output_folders, bucket_id, key, parent_id):
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
        progress_updater_with_size(count + 1, total, parent_id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _extract_task_name():
    """Strip off module information from current task name."""
    return current_task.name.split('.')[-1]


def _percent_to_real(percentage):
    """Convert an integer percentage to a real number from 0 to 1."""
    return percentage / 100
