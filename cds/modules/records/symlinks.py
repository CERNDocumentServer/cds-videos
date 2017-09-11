# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2017 CERN.
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

"""CDS record symlinks."""

import arrow
import os

from flask import current_app
from invenio_files_rest.models import FileInstance, Location


class SymlinksCreator(object):
    """."""

    def __init__(self):
        """Init."""
        self._symlinks_location = self._get_symlinks_location()

    def create(self, prev_record, new_record):
        """Create the video symlink with a human readable path."""
        accepted_context_types = ['master']

        # delete old symlink for previous record if any
        if prev_record:
            self._delete_prev_symlink(prev_record, accepted_context_types)

        for _file in new_record.get('_files', []):
            if _file.get('context_type', '') in accepted_context_types:
                self._create_symlink_for_file(_file, new_record)

    def _create_symlink_for_file(self, file, record):
        # fetch file location
        file_instance = FileInstance.get(file['file_id'])
        # build the new symlink path
        symlink_path = self._build_link_path(
            self._symlinks_location, record, file['key'])
        if file_instance and os.path.exists(file_instance.uri):
            source = file_instance.uri

            # build symlink path directories recursively
            if not os.path.isdir(os.path.dirname(symlink_path)):
                os.makedirs(os.path.dirname(symlink_path))

            info = "New symlink - source: {source}\nlink: {link}" \
                .format(source=source, link=symlink_path)
            current_app.logger.info(info)

            # delete the prev symlink for safety in case it points
            # to another file or it is broken
            self._delete_symlink(symlink_path)
            # create the new symlink
            os.symlink(source, symlink_path)

    def _delete_prev_symlink(self, prev_record, accepted_context_types):
        """Delete the symlink to the previous published file."""
        for _file in prev_record.get('_files', []):
            if _file.get('context_type', '') in accepted_context_types:
                link_name = self._build_link_path(self._symlinks_location,
                                                  prev_record, _file['key'])
                self._delete_symlink(link_name)

    @staticmethod
    def _delete_symlink(link_name):
        """Delete a symlink if it exists."""
        if os.path.lexists(link_name):
            info = "Deleting symlink\nlink: {link}\nWas pointing to: " \
                "{source}".format(link=link_name,
                                  source=os.path.realpath(link_name))
            current_app.logger.info(info)
            os.unlink(link_name)

    @staticmethod
    def _build_link_path(symlinks_location, record, filename):
        """Build the symlink path."""
        report_number = record['report_number'][0] if \
            len(record['report_number']) > 0 else record['report_number']
        year = arrow.get(record['date']).year

        return os.path.join(symlinks_location, record['type'],
                            record['category'], str(year), report_number,
                            filename)

    @staticmethod
    def _get_symlinks_location():
        """Set the video symlinks location."""
        links_dir_name = 'links'

        # go one dir up to set the links location
        # before: /path/to/videos/files
        # after: /path/to/videos/links
        videos_location = Location.get_by_name('videos')
        base_no_last, _ = os.path.split(videos_location.uri)
        return os.path.join(base_no_last, links_dir_name)
