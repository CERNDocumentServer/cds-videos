# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2018 CERN.
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

"""CDSDeposit app for Webhook receivers."""

import re
import mimetypes
import tempfile
import os
import shutil

from invenio_base.signals import app_loaded
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_files_rest.signals import file_uploaded
from invenio_files_rest.errors import InvalidKeyError
from invenio_indexer.signals import before_record_index
from invenio_records_files.utils import sorted_files_from_bucket
from srt_to_vtt import srt_to_vtt

from ..invenio_deposit.signals import post_action
from .indexer import cdsdeposit_indexer_receiver
from .receivers import (
    datacite_register_after_publish,
    index_deposit_after_action,
    register_celery_class_based_tasks,
    update_project_id_after_publish,
)


def _create_vtt_from_srt(srt_obj):
    """Create a VTT file from an SRT file.

    :param srt_obj: ObjectVersion of the SRT file
    :returns: ObjectVersion of the created VTT file or None
    """
    # Generate VTT filename from SRT filename
    vtt_key = srt_obj.key.rsplit(".", 1)[0] + ".vtt"

    # Check if VTT file already exists
    existing_vtt = ObjectVersion.get(srt_obj.bucket_id, vtt_key)
    if existing_vtt:
        # If it exists, skip
        return existing_vtt

    # Ensure the SRT file has a file instance
    if not srt_obj.file or not srt_obj.file.uri:
        return None

    srt_path = srt_obj.file.uri
    tmp_dir = None
    try:
        # Create temporary directory for VTT file
        tmp_dir = tempfile.mkdtemp()
        vtt_path = os.path.join(tmp_dir, vtt_key)

        # Convert using srt-to-vtt library
        srt_to_vtt(srt_path, vtt_path)

        # Create VTT ObjectVersion
        vtt_obj = ObjectVersion.create(
            bucket=srt_obj.bucket,
            key=vtt_key,
            stream=open(vtt_path, "rb"),
            size=os.path.getsize(vtt_path),
        )
        _create_tags(vtt_obj)
        return vtt_obj
    except (OSError, IOError, AttributeError, Exception):
        return None
    finally:
        # Clean up temporary directory
        if tmp_dir and os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass


def _create_tags(obj):
    """Create additional tags for file."""
    pattern_subtitle = re.compile(r".*_([a-zA-Z]{2})\.vtt$")
    pattern_poster = re.compile(r"^poster\.(jpg|png)$")

    # Get the media_type and content_type(file ext)
    file_name = obj.key
    mimetypes.add_type("subtitle/vtt", ".vtt")
    mimetypes.add_type("text/srt", ".srt")
    guessed_type = mimetypes.guess_type(file_name)[0]
    if guessed_type is None:
        raise InvalidKeyError(description=f"Unsupported File: {file_name}")

    media_type = guessed_type.split("/")[0]
    file_ext = guessed_type.split("/")[1]

    with db.session.begin_nested():
        ObjectVersionTag.create_or_update(obj, "content_type", file_ext)
        ObjectVersionTag.create_or_update(obj, "media_type", media_type)
        if file_ext == "vtt":
            # language tag
            match = pattern_subtitle.search(file_name)
            if match:
                ObjectVersionTag.create_or_update(obj, "language", match.group(1))
            else:
                ObjectVersionTag.delete(obj, "language")
            # other tags
            ObjectVersionTag.create_or_update(obj, "content_type", "vtt")
            ObjectVersionTag.create_or_update(obj, "context_type", "subtitle")
        elif file_ext == "srt":
            # Create VTT version from SRT
            try:
                _create_vtt_from_srt(obj)
            except Exception:
                pass
        # poster tag
        elif pattern_poster.match(file_name):
            ObjectVersionTag.create_or_update(obj, "context_type", "poster")

        db.session.add(obj)


def create_tags_on_file_upload(sender, obj):
    """Create additional tags when file is uploaded."""
    _create_tags(obj)
    db.session.commit()


class CDSDepositApp(object):
    """CDS deposit extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.extensions["cds-deposit"] = self
        self.register_signals(app)

    @staticmethod
    def register_signals(app):
        """Register CDS Deposit signals."""
        # index records after published
        # note: if publish a project -> index also videos
        post_action.connect(index_deposit_after_action, sender=app, weak=False)
        post_action.connect(update_project_id_after_publish, sender=app, weak=False)
        # if it's a project/video, expands information before index
        before_record_index.connect(cdsdeposit_indexer_receiver, sender=app, weak=False)
        # register Datacite after publish record
        post_action.connect(datacite_register_after_publish, sender=app, weak=False)

        # register class based celery tasks
        app_loaded.connect(register_celery_class_based_tasks)

        # file uploaded signal
        file_uploaded.connect(create_tags_on_file_upload)
