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

"""Webhooks utils."""

from __future__ import absolute_import

from contextlib import contextmanager
import tempfile
import shutil
import os

from invenio_db import db
from invenio_files_rest.models import ObjectVersionTag
from ..xrootd.utils import file_opener_xrootd


@contextmanager
def move_file_into_local(obj, delete=True):
    """Move file from XRootD accessed file system into a local path

    :param obj: Object version to make locally available.
    :param delete: Whether or not the tmp file should be deleted on exit.
    """
    if os.path.exists(obj.file.uri):
        yield obj.file.uri
    # TODO: remove migration hack
    # Check if we are migrating
    elif obj.get_tags().get('dfs_path', None):
        # This is a special situation!
        yield obj.get_tags().get('dfs_path', None)
    else:
        temp_location = obj.get_tags().get('temp_location', None)
        if not temp_location:
            temp_folder = tempfile.mkdtemp()
            temp_location = os.path.join(temp_folder, 'data')

            with open(temp_location, 'wb') as dst:
                shutil.copyfileobj(file_opener_xrootd(obj.file.uri, 'rb'), dst)

            ObjectVersionTag.create(obj, 'temp_location', temp_location)
            db.session.commit()
        else:
            temp_folder = os.path.dirname(temp_location)
        try:
            yield temp_location
        except:
            shutil.rmtree(temp_folder)
            ObjectVersionTag.delete(obj, 'temp_location')
            db.session.commit()
            raise
        else:
            if delete:
                shutil.rmtree(temp_folder)
                ObjectVersionTag.delete(obj, 'temp_location')
                db.session.commit()
