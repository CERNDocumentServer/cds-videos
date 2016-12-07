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

"""Response serialization."""

from collections import defaultdict

from invenio_records_rest.serializers import json_v1_response


def json_serializer(pid, record, *args, **kwargs):
    """Nest video owned files under each video."""
    if '_files' in record:
        # Sort by file key, first by length and then alphabetically
        record['_files'].sort(key=lambda f: (len(f['key']), f['key']))
        master_files = defaultdict(lambda: defaultdict(list))
        for file in record['_files']:
            master = file['tags'].get('master')
            # Append to master's files if it's a child, otherwise update master
            if master:
                master_files[master][file['tags']['type']].append(file)
            else:
                master_files[file['version_id']].update(file)
        record['_files'] = master_files.values()
    return json_v1_response(pid, record, *args, **kwargs)
