# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
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

from celery.utils.log import get_task_logger

from invenio_db import db

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.records.resolver import record_resolver
from cds.modules.webhooks.tasks import TranscodeVideoTask

logger = get_task_logger(__name__)


class MaintenanceTranscodeVideoTask(TranscodeVideoTask):
    """Transcode without indexing or sending sse messages."""

    def run(self, preset_quality, sleep_time=5, *args, **kwargs):
        super(MaintenanceTranscodeVideoTask, self).run(
            preset_quality=preset_quality,
            sleep_time=sleep_time,
            *args,
            **kwargs)

        logger.debug("Updating deposit and record")
        # get deposit and record
        dep_video = deposit_video_resolver(self.deposit_id)
        rec_video = record_resolver.resolve(dep_video['recid'])[1]
        # sync deposit --> record
        dep_video._sync_record_files(record=rec_video)
        dep_video.commit()
        rec_video.commit()
        db.session.commit()

    def on_success(self, *args, **kwargs):
        pass

    def _update_record(self, *args, **kwargs):
        pass
