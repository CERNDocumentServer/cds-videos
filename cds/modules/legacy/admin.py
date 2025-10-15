# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
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

"""Admin model views for CDSMigrationLegacyRecord."""

import html
import json

from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from invenio_admin.filters import FilterConverter
from invenio_pidstore.models import PersistentIdentifier
from markupsafe import Markup

from .models import CDSMigrationLegacyRecord


class CDSMigrationLegacyRecordModelView(ModelView):
    """Admin view for CDS Migration Legacy Records."""

    filter_converter = FilterConverter()
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    form_base_class = FlaskForm

    # recid_value (computed) instead of raw migrated_record_object_uuid
    column_list = (
        "id",
        "legacy_recid",
        "recid_value",
        "json_preview",
    )

    column_labels = {
        "id": "UUID",
        "legacy_recid": "Legacy Recid",
        "recid_value": "Migrated Record Recid",
        "json_preview": "Legacy Data (Preview of last dump)",
    }

    def _json_preview_formatter(self, context, model, name):
        """Display the last record's marcxml and a popup to view full JSON."""
        try:
            data = model.json or {}
            # Safely extract marcxml if exists
            marcxml = None
            records = data.get("record")
            if isinstance(records, list) and records:
                last_rec = records[-1] or {}
                marcxml = last_rec.get("marcxml")

            # Prepare pretty JSON for popup
            full_json = html.escape(json.dumps(data, indent=2))

            # Prepare short display text
            short_display = (
                f"<pre style='max-width:600px; "
                f"white-space: pre-wrap; overflow:hidden; text-overflow:ellipsis;'>"
                f"{html.escape((marcxml or '—')[:500])}</pre>"
            )

            # Build clickable popup trigger
            popup_html = f"""
            <div style="position:relative; display:inline-block;">
              <a href="#" onclick="document.getElementById('popup-{model.id}').style.display='block'; return false;">
                View full JSON
              </a>
              <div id="popup-{model.id}" 
                   style="display:none; position:fixed; top:5%; left:5%; width:90%; height:90%;
                          background:white; border:2px solid #888; padding:20px; overflow:auto; 
                          z-index:10000; box-shadow:0 0 10px rgba(0,0,0,0.5);">
                <a href="#" style="float:right; font-weight:bold; color:red; padding-left:10px; font-size:18px;"
                   onclick="document.getElementById('popup-{model.id}').style.display='none'; return false;">✖</a>
                <pre style='white-space: pre-wrap; font-size:13px;'>{full_json}</pre>
              </div>
            </div>
            """

            return Markup(short_display + popup_html)

        except Exception as e:
            return Markup(f"<i>Error rendering JSON: {html.escape(str(e))}</i>")

    def _recid_value_formatter(self, context, model, name):
        """Find the new recid PID for the migrated_record_object_uuid."""
        uuid = model.migrated_record_object_uuid
        if not uuid:
            return Markup("<i>—</i>")

        recid_pid = (
            self.session.query(PersistentIdentifier)
            .filter_by(
                object_uuid=uuid,
                object_type="rec",
                pid_type="recid",
            )
            .first()
        )

        if recid_pid:
            # clickable link to record page
            url = f"/admin/recordmetadata/details/?id={uuid}"
            return Markup(f'<a href="{url}" target="_blank">{recid_pid.pid_value}</a>')
        else:
            return Markup("<i>not mapped</i>")

    def _legacy_recid_formatter(self, context, model, name):
        """Make legacy_recid clickable (/legacy/record/<legacy_recid>)."""
        if not model.legacy_recid:
            return Markup("<i>—</i>")
        url = f"/legacy/record/{model.legacy_recid}"
        return Markup(f'<a href="{url}" target="_blank">{model.legacy_recid}</a>')

    column_formatters = {
        "json_preview": _json_preview_formatter,
        "recid_value": _recid_value_formatter,
        "legacy_recid": _legacy_recid_formatter,
    }

    column_searchable_list = ("legacy_recid",)
    column_sortable_list = ("legacy_recid", "id")
    column_default_sort = ("legacy_recid", True)
    page_size = 25


cds_migration_legacy_record_model_view = dict(
    modelview=CDSMigrationLegacyRecordModelView,
    model=CDSMigrationLegacyRecord,
    name="Legacy Records",
    category="CDS Migration",
)
