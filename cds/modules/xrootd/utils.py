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

"""XrootD utilities."""

from flask import current_app


def replace_xrootd(path):
    """Replace XRootD path.

    :param path: The file path.

    .. note::

        This will only work if XRootD is enabled.
    """
    if current_app.config['XROOTD_ENABLED']:
        return path.replace(
            current_app.config['VIDEOS_XROOTD_PREFIX'],
            current_app.config['VIDEOS_LOCATION'],
        )
    return path


def file_opener_xrootd(path):
    """File opener from XRootD path.

    :param path: The file path for the opener.
    :returns: an open file

    .. note::

        This will return an open file via ``XRootDPyFS`` if XRootD is
        enabled.
    """
    if current_app.config['XROOTD_ENABLED']:
        from xrootdpyfs import XRootDPyFS
        # Get the filename
        _filename = path.split('/')[-1]
        # Remove filename from the path
        path = path.replace(_filename, '')
        fs = XRootDPyFS(path)
        return fs.open('data')
    # No XrootD return a normal file
    return open(path, 'r')
