# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Deposit Indexer."""

from __future__ import absolute_import, print_function

from invenio_jsonschemas import current_jsonschemas

from .api import Video, Project


def cdsdeposit_indexer_receiver(
        sender, json=None, record=None, index=None, **dummy_kwargs):
    """Inject task status information before index."""
    video_schema = current_jsonschemas.path_to_url(Video._schema)
    project_schema = current_jsonschemas.path_to_url(Project._schema)
    if record['$schema'] == project_schema:
        deposit = Project.get_record(record.id)
    if record['$schema'] == video_schema:
        deposit = Video.get_record(record.id)
    if record['$schema'] in [project_schema, video_schema]:
        json['_deposit']['state'] = deposit['_deposit']['state']
        json['_files'] = deposit['_files']
