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

from __future__ import absolute_import, print_function

from invenio_base.signals import app_loaded
from invenio_deposit.signals import post_action
from invenio_indexer.signals import before_record_index

from .indexer import cdsdeposit_indexer_receiver
from .receivers import (datacite_register_after_publish,
                        index_deposit_after_action,
                        register_celery_class_based_tasks,
                        update_project_id_after_publish)


class CDSDepositApp(object):
    """CDS deposit extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.extensions['cds-deposit'] = self
        self.register_signals(app)

    @staticmethod
    def register_signals(app):
        """Register CDS Deposit signals."""
        # index records after published
        # note: if publish a project -> index also videos
        post_action.connect(index_deposit_after_action,
                            sender=app, weak=False)
        post_action.connect(update_project_id_after_publish,
                            sender=app, weak=False)
        # if it's a project/video, expands information before index
        before_record_index.connect(
            cdsdeposit_indexer_receiver, sender=app, weak=False)
        # register Datacite after publish record
        post_action.connect(
            datacite_register_after_publish, sender=app, weak=False)

        # register class based celery tasks
        app_loaded.connect(register_celery_class_based_tasks)
