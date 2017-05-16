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

"""Python FFmpeg wrapper errors."""

from __future__ import absolute_import


class FFmpegError(Exception):
    """General FFmpeg error class."""


class FFmpegExecutionError(Exception):
    """Raised when there is an execution error of an FFmpeg subprocess."""

    def __init__(self, process_error):
        self.internal_error = process_error
        self.cmd = ' '.join(process_error.cmd)
        self.error_code = process_error.returncode
        self.error_message = process_error.output.decode('utf-8')

    def __repr__(self):
        return ('COMMAND: {0}\n'
                'ERROR_CODE: {1}\n'
                'OUTPUT: {2}'
                ).format(self.cmd, self.error_code, self.error_message)

    def __str__(self):
        return self.__repr__()


class FrameExtractionInvalidArguments(FFmpegError):
    """Raised when invalid arguments are passed to ff_frames."""


class MetadataExtractionExecutionError(FFmpegExecutionError):
    """Raised when there is an execution error of a ff_probe subprocess."""


class FrameExtractionExecutionError(FFmpegExecutionError):
    """Raised when there is an execution error of a ff_frames subprocess."""
