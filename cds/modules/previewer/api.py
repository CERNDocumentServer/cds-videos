# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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

"""CDS Previewer API."""

from __future__ import absolute_import, print_function

from flask import current_app, url_for

from invenio_previewer.api import PreviewFile


class CDSPreviewRecordFile(PreviewFile):
    """Preview deposit files implementation."""

    @property
    def uri(self):
        """Get file download link."""
        return url_for(
            'invenio_records_ui.{0}_files'.format(self.pid.pid_type),
            pid_value=self.pid.pid_value,
            filename=self.file.key)


class CDSPreviewDepositFile(PreviewFile):
    """Preview deposit files implementation."""

    @property
    def uri(self):
        """Get file download link.
        ..  note::
            This is only for ```<pid_type:depid>``` records
        """
        uri = "{api}/{bucket}/{key}".format(
            api=current_app.config['DEPOSIT_FILES_API'],
            bucket=str(self.file.bucket),
            key=self.file.key
        )
        return uri
