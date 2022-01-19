# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2021 CERN.
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

"""Errors for Opencast."""

from __future__ import absolute_import, print_function


class OpencastError(Exception):
    """Base class for exceptions in this module."""

    pass


class MissingEventId(OpencastError):
    """Error for missing event id."""

    def __init__(self, task_id):
        """Initialize exception with task id."""
        self.task_id = task_id

    def __str__(self):
        """Error message."""
        return "Opencast event id is missing in Task with id: {0} .".format(
            self.task_id
        )


class MissingResolutionError(OpencastError):
    """Error for invalid resolutions."""

    def __init__(self, resolution):
        """Initialize exception with resolution."""
        self.resolution = resolution

    def __str__(self):
        """Error message."""
        return "Resolution not support {0}.".format(self.resolution)


class TooHighResolutionError(OpencastError):
    """The resolution is over the required maximum."""

    def __init__(self, max_height, max_width, height, width):
        """Initialize exception."""
        self._max_height = max_height
        self._max_weight = max_width
        self._height = height
        self._width = width

    def __str__(self):
        """Error message."""
        return (
            "Resolution {1}x{2} is higher than the maximum resolution accepted"
            " {3}x{4}."
        ).format(self._width, self._height, self._max_weight, self._max_height)


class RequestError(OpencastError):
    """Error while performing ingest request in Opencast."""

    def __init__(self, url, exception):
        self.url = url
        self.exception = exception

    def __str__(self):
        request = self.exception.request
        req = "URL <{0}>\nBody {1}".format(request.url, request.body)
        response = self.exception.response
        resp = "Code <{0}>\nBody {1}".format(
            response.status_code, response.text
        )
        return "Failed request to {0}.\nRequest: {1}\nResponse: {2}".format(
            self.url, req, resp
        )


class RequestError404(RequestError):
    """404 error while performing a request in Opencast."""


class WriteToEOSError(OpencastError):
    """Error while writing transcoded file to EOS."""

    def __init__(self, url, message):
        self.url = url
        self.message = message

    def __str__(self):
        return (
            "Failed to write transcoded file to EOS Request failed on: "
            "{0}. Error message: {1}"
        ).format(self.url, self.message)


class AbruptCeleryStop(OpencastError):
    """Abrupt celery error."""

    def __init__(self, task_id):
        self.task_id = task_id

    def __str__(self):
        return (
            "Abrupt celery stop while processing task with id: {1}"
        ).format(self.task_id)
