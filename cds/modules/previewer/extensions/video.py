# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Previews video files."""

from __future__ import absolute_import, print_function

from flask import render_template


class VideoExtension(object):
    """Previewer extension for videos."""

    previewable_extensions = ['mp4', 'm4v', 'webm', 'mov', 'avi', 'mpg', 'flv',
                              'ts']
    _file_exts = ['.{0}'.format(ext) for ext in previewable_extensions]

    def __init__(self, template=None):
        """Init video previewer."""
        self.template = template

    def can_preview(self, file):
        """Determine if the given file can be previewed."""
        return file.is_local() and file.has_extensions(*self._file_exts)

    def preview(self, file, embed_config=None):
        """Render appropriate template with embed flag."""
        record = getattr(file, 'record')
        filename = getattr(file, 'filename', '')
        file_extension = filename.split('.')[-1] \
            if filename and '.' in filename else ''
        report_number = record['report_number'][0] \
            if 'report_number' in record and len(record['report_number']) \
            else ''

        return render_template(
            self.template,
            file=file,
            css_bundles=['cds_previewer_video_css'],
            file_extension=file_extension,
            recid=record.get('recid', ''),
            report_number=report_number,
            record=record,
            embed_config=embed_config,
        )


video = VideoExtension('cds_previewer/video/internal.html')
embed_video = VideoExtension('cds_previewer/video/embed.html')
deposit_video = VideoExtension('cds_previewer/video/deposit.html')
