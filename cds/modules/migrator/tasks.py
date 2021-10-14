# -*- coding: utf-8 -*-

#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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
"""Record migration special."""

import warnings

from celery import shared_task
from invenio_db import db
from invenio_migrator.proxies import current_migrator

from ..deposit.api import deposit_video_resolver
from ..records.resolver import record_resolver
from ..flows.tasks import TranscodeVideoTask

warnings.warn(
    "The migrator module is now deprecated. Use it at your own risk!",
    DeprecationWarning)


class TranscodeVideoTaskQuiet(TranscodeVideoTask):
    """Transcode without index or send sse messages."""

    def run(self, preset_quality, sleep_time=5, *args, **kwargs):
        super(TranscodeVideoTaskQuiet, self).run(
            preset_quality=preset_quality,
            sleep_time=sleep_time,
            *args,
            **kwargs)
        # get deposit and record
        video = deposit_video_resolver(self.deposit_id)
        rec_video = record_resolver.resolve(video['recid'])[1]
        # sync deposit --> record
        video._sync_record_files(record=rec_video)
        video.commit()
        rec_video.commit()
        db.session.commit()

    def on_success(self, *args, **kwargs):
        pass

    def _update_record(self, *args, **kwargs):
        pass


@shared_task(ignore_result=True)
def clean_record(data, source_type):
    """Delete all information related with a given record.

    Note: files are deleted from the file system
    """
    try:
        source_type = source_type or 'marcxml'
        assert source_type in ['marcxml', 'json']

        recorddump = current_migrator.records_dump_cls(
            data,
            source_type=source_type,
            pid_fetchers=current_migrator.records_pid_fetchers, )
        current_migrator.records_dumploader_cls.clean(
            recorddump, delete_files=True)

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
