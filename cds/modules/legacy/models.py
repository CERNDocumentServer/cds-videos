# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2025 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS Migration models."""

import json
import uuid

from invenio_db import db
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.types import UUIDType


class CDSMigrationLegacyRecord(db.Model):
    """Store the extracted legacy information for a specific record."""

    __tablename__ = "cds_migration_legacy_records"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    migrated_record_object_uuid = Column(
        UUIDType,
        nullable=True,
        comment="The uuid of the migrated record metadata.",
    )
    legacy_recid = Column(
        Integer, nullable=True, comment="The record id in the legacy system"
    )
    json = db.Column(
        db.JSON().with_variant(
            postgresql.JSONB(none_as_null=True),
            "postgresql",
        ),
        default=lambda: dict(),
        nullable=True,
        comment="The extracted information of the legacy record before any transformation.",
    )

    def __repr__(self):
        """Representation of the model."""
        return f"<CDSMigrationLegacyRecord legacy_recid={self.legacy_recid} migrated_record_object_uuid={self.migrated_record_object_uuid} json={json.dumps(self.json)}>"
