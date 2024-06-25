# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Maintenance tasks."""

import os
import shutil
import time

from celery import current_app, shared_task

from cds.modules.flows.files import CDS_FILES_TMP_FOLDER


@shared_task(ignore_result=True)
def clean_tmp_videos():
    """Delete old processed videos in the tmp folder."""
    now = time.time()
    SEVEN_DAYS_AGO = now - 7 * 60 * 60 * 24

    if not os.path.exists(current_app.config["CDS_FILES_TMP_FOLDER"]):
        return

    for folder in os.listdir(current_app.config["CDS_FILES_TMP_FOLDER"]):
        path = os.path.join(current_app.config["CDS_FILES_TMP_FOLDER"], folder)
        if not os.path.isdir(path):
            continue

        last_modification_time = os.stat(path).st_mtime
        to_delete = last_modification_time < SEVEN_DAYS_AGO
        if to_delete:
            shutil.rmtree(path)
