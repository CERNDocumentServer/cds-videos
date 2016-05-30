# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""Record Loader."""

from __future__ import absolute_import, print_function

import arrow
from cds_dojson.marc21 import marc21
from cds_dojson.to_marc21 import to_marc21
from dojson.contrib.marc21.utils import create_record
from flask import current_app
from invenio_migrator.records import RecordDump


class CDSRecordDump(RecordDump):
    """CDS record dump class."""

    def __init__(self, data, source_type='marcxml', latest_only=False,
                 pid_fetchers=None, dojson_model=marc21):
        """Initialize."""
        super(self.__class__, self).__init__(
                data, source_type, latest_only, pid_fetchers, dojson_model)

    def _prepare_intermediate_revision(self, data):
        dt = arrow.get(data['modification_datetime']).datetime

        if self.source_type == 'marcxml':
            marc_record = create_record(data['marcxml'])
            try:
                val = self.dojson_model.do(marc_record)
            except Exception as e:
                current_app.logger.warning(
                    'Impossible to convert to JSON {0} - {1}, saving '
                    'intermediate version as MAR21'.format(e, marc_record))
                return (dt, marc_record)

            missing = self.dojson_model.missing(marc_record)
            for field in missing:
                current_app.logger.warning(
                    'Adding field {0} to intermediate version {1}'.format(
                        field, val['control_number']))
                val[field] = marc_record[field]

            # Don't validate intermediate versions
            del val['$schema']
        else:
            val = data['json']

        return (dt, val)

    def _prepare_final_revision(self, data):
        dt = arrow.get(data['modification_datetime']).datetime

        if self.source_type == 'marcxml':
            marc_record = create_record(data['marcxml'])
            try:
                val = self.dojson_model.do(marc_record)
            except Exception as e:
                current_app.logger.error(
                    'Impossible to convert to JSON {0} - {1}'.format(
                        e, marc_record))
                raise

            lossy_fields = []
            back_marc_record = to_marc21.do(val)
            for key, value in marc_record.items():
                if value != back_marc_record.get(key):
                    lossy_fields.append((key, value, back_marc_record.get(key)))

            if lossy_fields:
                current_app.logger.error(
                    'Lossy conversion: {0} {1}'.format(
                        val['control_number'], lossy_fields))
                # raise RuntimeError('Lossy conversion')

            # TODO: add schema once ready
            del val['$schema']
        else:
            val = data['json']

        return (dt, val)

    def prepare_revisions(self):
        """Prepare data.

        If DoJSON fails to create a revision, which is not the last one, a
        version of MARC21 will be stored as JSON directly without any
        translation.

        If the translation succeeds and there are missing fields for the older
        revisions, old MARC21 missing fields will be added to the JSON.

        In both cases, if the revisions is the last one, an error will be
        generated as the final translation is not complete.
        """
        # Prepare revisions
        self.revisions = []

        it = [self.data['record'][0]] if self.latest_only \
            else self.data['record']

        for i in it[:-1]:
            self.revisions.append(self._prepare_intermediate_revision(i))

        self.revisions.append(self._prepare_final_revision(it[-1]))
