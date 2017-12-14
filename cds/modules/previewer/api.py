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

import re
from os import symlink
from os.path import exists, join, relpath, split

from flask import current_app, url_for
from invenio_files_rest.models import ObjectVersion, as_object_version

from invenio_previewer.api import PreviewFile


def get_relative_path(object_version):
    """Get ObjectVersion's full path relative to its bucket location."""
    object_version = as_object_version(object_version)
    location_root = object_version.bucket.location.uri
    filepath, filename = split(object_version.file.uri)
    relative_path = relpath(filepath, location_root)
    return join(relative_path, filename)


class CDSPreviewRecordFile(PreviewFile):
    """Preview record files implementation."""

    @property
    def subformats(self):
        """Get the subformats."""
        return self.file.dumps().get('subformat', [])

    @property
    def uri(self):
        """Get file download link."""
        return url_for(
            'invenio_records_ui.{0}_files'.format(self.pid.pid_type),
            pid_value=self.pid.pid_value,
            filename=self.file.key)

    @property
    def m3u8_uri(self):
        """Get m3u8 playlist link."""
        smil_obj = self.smil_file_object
        if smil_obj:
            wowza_url = current_app.config['WOWZA_PLAYLIST_URL']
            filepath = get_relative_path(smil_obj)
            return wowza_url.format(filepath='{0}'.format(filepath))

    @property
    def poster_uri(self):
        """Get video's poster link."""
        try:
            return [f['links']['self']
                    for f in self.record['_files']
                    if f['context_type'] == 'poster'][0]
        except IndexError:
            return url_for(
                'invenio_records_ui.{0}_files'.format(self.pid.pid_type),
                pid_value=self.pid.pid_value,
                filename='frame-1.jpg')

    @property
    def record_uri(self):
        """Get the record uri."""
        return url_for(
            'invenio_records_rest.recid_item',
            pid_value=self.pid.pid_value,
            _external=True
        )

    @property
    def embed_uri(self):
        """Get the embed uri."""
        return url_for(
            'invenio_records_ui.recid_preview',
            pid_value=self.pid.pid_value,
            filename=self.file.key,
            _external=True
        )

    @property
    def thumbnails_uri(self):
        """Get video's thumbnails' link."""
        return url_for(
            'invenio_records_ui.{0}_export'.format(self.pid.pid_type),
            pid_value=self.pid.pid_value, format='vtt', raw=True)

    @property
    def subtitles(self):
        """Get video's subtitles."""
        return [(f['links']['self'], f['tags']['language'])
                for f in self.record['_files']
                if f['context_type'] == 'subtitle' and 'language' in f['tags']]

    @property
    def smil_file_object(self):
        """Get corresponding SMIL file."""
        data = self.file.dumps()
        if 'playlist' in data:
            smil_info = data['playlist'][0]
            return ObjectVersion.get(smil_info['bucket_id'], smil_info['key'])

    @property
    def vr(self):
        """Get video's VR flag."""
        return self.record.get('vr')


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

    @property
    def subtitles(self):
        """Get video's subtitles."""
        pattern = re.compile(".*_([a-zA-Z]{2})\.vtt$")

        def get_subtitle_tuple(f):
            """Get URL and language of a subtitle file."""
            found = pattern.findall(f['key'])
            lang = found[0] if len(found) == 1 else ''
            return f['links']['self'], lang

        return [get_subtitle_tuple(f) for f in self.record['_files']
                if f['content_type'] == 'vtt']
