# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2018 CERN.
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

"""CDS files rest app for file download receivers."""

from __future__ import absolute_import, print_function

from invenio_files_rest.signals import file_downloaded

from .receivers import on_download_rename_file


class CDSFilesRestApp(object):
    """CDS files rest extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.extensions['cds-files-rest'] = self
        self.register_signals(app)

    @staticmethod
    def register_signals(app):
        """Register CDS files rest signals."""
        file_downloaded.connect(
            on_download_rename_file, sender=app, weak=False)
