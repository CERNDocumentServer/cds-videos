# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
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

"""Webhook errors."""


class FlowsError(Exception):
    """General webhook error."""


class FlowDoesNotExist(FlowsError):
    """Raised when receiver does not exist."""


class InvalidPayload(FlowsError):
    """Raised when the payload is invalid."""


class ExtractMetadataTaskError(FlowsError):
    """Raised when the extract metadata task ."""


class ExtractFramesTaskError(FlowsError):
    """Raised when the extract frames task ."""


class TaskAlreadyRunningError(FlowsError):
    """Raised when a task is restarted while is running."""
