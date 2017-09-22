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
import logging
import os

from invenio_files_rest.models import FileInstance, Location

from cds.modules.xrootd.utils import replace_xrootd

logger = logging.getLogger("cds-symlink-creator")


class SymlinksCreator(object):
    """Create symlinks for files."""

    accepted_context_types = ['master']

    def __init__(self):
        """Init."""
        self._symlinks_location = self._get_symlinks_location()

    def create(self, prev_record, new_record):
        """Create the video symlink with a human readable path."""
        # delete old symlink for previous record if any
        if prev_record:
            self._delete_prev_symlink(prev_record, self.accepted_context_types)
        # create new symlinks
        for _file in self._get_list_files(record=new_record):
            self._create_symlink_for_file(_file, new_record)

    @classmethod
    def _get_list_files(cls, record):
        """Get the list of file that need symlinks."""
        for _file in record.get('_files', []):
            if _file.get('context_type', '') in cls.accepted_context_types:
                yield _file

    def _create_symlink_for_file(self, file, record):
        """Create a new symlink for a given file"""

        logger.info("Creating symlink for a new file")

        # fetch file location
        file_instance = FileInstance.get(file['file_id'])

        # build the new symlink path
        symlink_path = self._build_link_path(
            self._symlinks_location, record, file['key'])

        source_real_file_path = replace_xrootd(file_instance.uri)
        logger.debug("Creating symlink for file path: {file_path}"
                     .format(file_path=source_real_file_path))

        if os.path.exists(source_real_file_path):
            # build symlink path directories recursively
            if not os.path.isdir(os.path.dirname(symlink_path)):
                os.makedirs(os.path.dirname(symlink_path))

            # delete the prev symlink for safety in case it points
            # to another file or it is broken
            self._delete_symlink(symlink_path)

            logger.info("New symlink - source: {source}\nlink: {link}"
                        .format(source=source_real_file_path,
                                link=symlink_path))

            # create the new symlink
            os.symlink(source_real_file_path, symlink_path)
        else:
            logger.error("File path not found: {file_path}"
                         .format(file_path=source_real_file_path))

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
        real_link_name = replace_xrootd(link_name)
        path_exists = os.path.lexists(real_link_name)

        logger.debug("Checking old symlink, does {link_name} exist? "
                     "{exists}".format(link_name=real_link_name,
                                       exists=path_exists))
        if path_exists:
            info = "Deleting symlink\nlink: {link}\nWas pointing to: " \
                "{source}".format(link=real_link_name,
                                  source=os.path.realpath(real_link_name))
            logger.info(info)
            os.unlink(real_link_name)

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
        real_videos_location = replace_xrootd(videos_location.uri).rstrip('/')

        base_no_last, _ = os.path.split(real_videos_location)
        symlinks_location = os.path.join(base_no_last, links_dir_name)

        logger.debug("Symlinks location: {loc}".format(loc=symlinks_location))
        return symlinks_location
