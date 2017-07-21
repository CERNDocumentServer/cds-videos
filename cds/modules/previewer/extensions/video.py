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

    previewable_extensions = ['mp4', 'webm', 'mov']

    def __init__(self, template=None, embed=False):
        self.embed = embed
        self.template = template

    @staticmethod
    def can_preview(file):
        """Determine if the given file can be previewed."""
        return file.is_local() and file.has_extensions('.mp4', '.webm', '.mov')

    def preview(self, file):
        """Render appropriate template with embed flag."""
        return render_template(
            self.template,
            file=file,
            video_url=file.uri,
            m3u8_url=getattr(file, 'm3u8_uri', None),
            thumbnails_url=getattr(file, 'thumbnails_uri', None),
            poster_url=getattr(file, 'poster_uri', None),
            embed_url=getattr(file, 'embed_uri', None),
            subtitles=getattr(file, 'subtitles', []),
            embed=self.embed,
            vr=getattr(file, 'vr', False),
            css_bundles=['cds_previewer_video_css'],
        )


video = VideoExtension('cds_previewer/video.html')
embed_video = VideoExtension('cds_previewer/embedded_video.html', embed=True)
deposit_video = VideoExtension('cds_previewer/deposit_video.html')
