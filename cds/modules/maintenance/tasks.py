# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018, 2020 CERN.
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

"""Tasks for maintenance scripts."""
from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.flows.models import Status
from cds.modules.flows.tasks import TranscodeVideoTask
from cds.modules.records.resolver import record_resolver
from celery import shared_task
from celery.utils.log import get_task_logger
from invenio_db import db

logger = get_task_logger(__name__)


@shared_task
class MaintenanceTranscodeVideoTask(TranscodeVideoTask):
    """Transcode without indexing."""

    def run(self, *args, **kwargs):
        super(MaintenanceTranscodeVideoTask, self).run(*args, **kwargs)

        logger.debug("Updating deposit and record")
        # get deposit and record
        dep_video = deposit_video_resolver(self.deposit_id)
        if "recid" in dep_video:
            rec_video = record_resolver.resolve(dep_video["recid"])[1]
            # sync deposit --> record
            dep_video._sync_record_files(record=rec_video)
            rec_video.commit()

        dep_video.commit()
        db.session.commit()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task_id = kwargs.get("task_id", task_id)
        self.commit_status(task_id, Status.FAILURE, str(einfo))
