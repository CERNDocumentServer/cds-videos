# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Record resolver."""

from __future__ import absolute_import, print_function

from functools import partial
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.resolver import Resolver

from .api import Keyword, CDSRecord


def get_pid(pid_type, pid_value):
    """Get all pids."""
    return PersistentIdentifier.query.filter_by(
        pid_type=pid_type, pid_value=pid_value
    ).one()


keyword_resolver = Resolver(
    pid_type='kwid', object_type='rec',
    getter=partial(Keyword.get_record, with_deleted=True)
)


record_resolver = Resolver(
    pid_type='recid', object_type='rec',
    getter=partial(CDSRecord.get_record, with_deleted=True)
)


get_record_pid = partial(get_pid, pid_type='recid')
