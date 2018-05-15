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

from invenio_indexer.api import RecordIndexer
from invenio_indexer.tasks import index_record
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.models import PersistentIdentifier

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
        json['_cds']['state'] = deposit['_cds']['state']
        json['_files'] = deposit['_files']


class CDSRecordIndexer(RecordIndexer):
    """Cds record indexer class."""

    def _index_project_after_publish(self, deposit):
        # index videos (records)
        pid_values = Project(data=deposit).video_ids
        ids = [
            str(p.object_uuid) for p in PersistentIdentifier.query.filter(
                PersistentIdentifier.pid_value.in_(pid_values)).all()
        ]
        # index project (record)
        _, record = deposit.fetch_published()
        ids.append(str(record.id))
        # index project (deposit)
        ids.append(str(deposit.id))
        super(CDSRecordIndexer, self).bulk_index(iter(ids))

    def index(self, deposit, action='commit'):
        video_schema = current_jsonschemas.path_to_url(Video._schema)
        project_schema = current_jsonschemas.path_to_url(Project._schema)
        if action == 'publish':
            if deposit['$schema'] == project_schema:
                self._index_project_after_publish(deposit)
            elif deposit['$schema'] == video_schema:
                _, record = deposit.fetch_published()
                super(CDSRecordIndexer, self).index(record)
        elif action in ('edit', 'discard', 'commit'):
            super(CDSRecordIndexer, self).index(deposit)
        elif action == 'delete':
            self.delete(deposit)

    def delete(self, record):
        video_schema = current_jsonschemas.path_to_url(Video._schema)
        project_schema = current_jsonschemas.path_to_url(Project._schema)
        if record['$schema'] == video_schema:
            project = record.project
            super(CDSRecordIndexer, self).delete(record)
            # If is a Video index also the project
            super(CDSRecordIndexer, self).index(project)
        elif record['$schema'] == project_schema:
            ids = [str(video.id) for video in record.videos]
            if ids:
                index, doc_type = self.record_to_index(record.videos[0])
                self.bulk_delete(iter(ids), index=index, doc_type=doc_type)
            super(CDSRecordIndexer, self).delete(record)

    def bulk_delete(self, record_iterator, **kwargs):
        """Overrides to `RecordIndexer.buld_delete` to pass the index of the
        records. Can be used to delete only records of the same index."""
        self._bulk_op(record_id_iterator, 'delete', **kwargs)
