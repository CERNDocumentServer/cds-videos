# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
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

"""CDS files rest receivers."""

from __future__ import absolute_import, print_function

from os.path import splitext

from invenio_files_rest.models import as_object_version


def on_download_rename_file(sender, obj):
    """Rename files generated from master file when downloading."""
    master_version_id = obj.get_tags().get('master') if obj else None
    if master_version_id:
        master_obj = as_object_version(master_version_id)
        filename_no_ext = splitext(master_obj.key)[0]
        # master filename is the report number
        if filename_no_ext not in obj.key:
            obj.key = '{}-{}'.format(filename_no_ext, obj.key)
