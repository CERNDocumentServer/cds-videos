# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS tests for Webhook receivers."""

from __future__ import absolute_import, print_function

import uuid

from cds_sorenson.api import get_available_preset_qualities
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from six import BytesIO
from celery import shared_task, states
from cds.modules.deposit.minters import catid_minter
from invenio_indexer.api import RecordIndexer
from invenio_db import db
from cds.modules.webhooks.tasks import AVCTask
from cds.modules.deposit.api import Category
from cds.modules.webhooks.tasks import TranscodeVideoTask


@shared_task(bind=True)
def failing_task(self, *args, **kwargs):
    """A failing shared task."""
    self.update_state(state=states.FAILURE, meta={})


@shared_task(bind=True)
def success_task(self, *args, **kwargs):
    """A failing shared task."""
    self.update_state(state=states.SUCCESS, meta={})


class sse_failing_task(AVCTask):

    def __init__(self):
        self._type = 'simple_failure'
        self._base_payload = {}

    def run(self, *args, **kwargs):
        """A failing shared task."""
        pass

    def on_success(self, exc, task_id, *args, **kwargs):
        """Set Fail."""
        self.update_state(
            state=states.FAILURE,
            meta={'exc_type': 'fuu', 'exc_message': 'fuu'})


class sse_success_task(AVCTask):

    def __init__(self):
        self._type = 'simple_failure'
        self._base_payload = {}

    def run(self, *args, **kwargs):
        """A failing shared task."""
        self.update_state(state=states.SUCCESS, meta={})


@shared_task
def simple_add(x, y):
    """Simple shared task."""
    return x + y


class sse_simple_add(AVCTask):
    def __init__(self):
        self._type = 'simple_add'
        self._base_payload = {}

    def run(self, x, y, **kwargs):
        """Simple shared task."""
        self._base_payload = {"deposit_id": kwargs.get('deposit_id')}
        return x + y


def create_category(api_app, db, data):
    """Create a fixture for category."""
    with db.session.begin_nested():
        record_id = uuid.uuid4()
        catid_minter(record_id, data)
        category = Category.create(data)

    db.session.commit()

    indexer = RecordIndexer()
    indexer.index_by_id(category.id)

    return category


def mock_current_user(*args2, **kwargs2):
    """Mock current user not logged-in."""
    return None


def transcode_task(bucket, filesize, filename, preset_qualities):
    """Get a transcode task."""
    obj = ObjectVersion.create(bucket, key=filename,
                               stream=BytesIO(b'\x00' * filesize))
    ObjectVersionTag.create(obj, 'display_aspect_ratio', '16:9')
    obj_id = str(obj.version_id)
    db.session.commit()

    return (obj_id, [
        TranscodeVideoTask().s(
            version_id=obj_id, preset_quality=preset_quality, sleep_time=0)
        for preset_quality in preset_qualities
    ])


def get_object_count(download=True, frames=True, transcode=True):
    """Get number of ObjectVersions, based on executed tasks."""
    return sum([
        1 if download else 0,
        90 if frames else 0,
        len(get_available_preset_qualities()) if transcode else 0,
    ])


def get_tag_count(download=True, metadata=True, frames=True, transcode=True):
    """Get number of ObjectVersionTags, based on executed tasks."""
    return sum([
        2 if download else 0,
        10 if download and metadata else 0,
        90 * 2 if frames else 0,
        len(get_available_preset_qualities()) * 4 if transcode else 0,
    ])
