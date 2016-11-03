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

from __future__ import absolute_import

import requests
from celery import shared_task
from invenio_files_rest.models import as_object_version


@shared_task(bind=True)
def download_to_object_version(self, url, object_version, **kwargs):
    r"""Download file from a URL.

    :param url: URL of the file to download.
    :param object_version: ``ObjectVersion`` instance or object version id.
    :param chunk_size: Size of the chunks for downloading.
    :param \**kwargs:
    """
    obj = as_object_version(object_version)

    # Make HTTP request
    response = requests.get(url, stream=True)
    total = int(response.headers.get('Content-Length'))

    def progress_updater(size, total):
        """Progress reporter."""
        meta = dict(
            size=size,
            total=total,
            percentage=size / total * 100,
            task_id=self.task_id,
            envent_id=kwargs.get('event_id', None),
            message='Downloading {0} of {1}'.format(size, total), )

        self.update_state(state=state('STARTED'), meta=meta)

    obj.set_contents(response.content, progress_callback=progress_updater)

    db.session.commit()

    # Return downloaded file location
    return object_version
