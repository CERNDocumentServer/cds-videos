# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017, 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Records UI."""

from __future__ import absolute_import, print_function

import six
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    render_template,
    request,
)
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_pidstore.resolver import Resolver
from werkzeug.utils import import_string

from ..deposit.api import Project, Video
from ..deposit.fetcher import deposit_fetcher
from .forms import RecordDeleteForm
from .utils import delete_project_record, delete_video_record, is_project_record

blueprint = Blueprint(
    "cds_records",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@blueprint.app_template_filter("pidstatus")
def pidstatus_title(pid):
    """Get PID status full name."""
    if pid:
        return PIDStatus(pid.status).title
    return None


# NOTE: Disable record statistics page
# def stats_recid(pid, record, template=None, **kwargs):
#     """Preview file for given record."""
#     return render_template("cds_records/record_stats.html", record=record)


def records_ui_export(pid, record, template=None, **kwargs):
    """Export a record."""
    formats = current_app.config.get("CDS_RECORDS_EXPORTFORMATS")
    fmt = request.view_args.get("format")

    if formats.get(fmt) is None:
        return (
            render_template("cds_records/records_export_unsupported.html"),
            410,
        )
    else:
        serializer = import_string(formats[fmt]["serializer"])
        data = serializer.serialize(pid, record)
        if "raw" in request.args:
            response = make_response(data)
            response.headers["Content-Type"] = formats[fmt]["mimetype"]
            return response
        else:
            if isinstance(data, six.binary_type):
                data = data.decode("utf8")

            return render_template(
                template,
                pid=pid,
                record=record,
                data=data,
                format_title=formats[fmt]["title"],
            )


def records_ui_delete(pid, record, template=None, **kwargs):
    """Delete a record."""
    pids = [pid]
    try:
        pids.append(PersistentIdentifier.get("doi", record["doi"]))
    except (PIDDoesNotExistError, KeyError):
        # Dealing with a project?
        pass

    try:
        pids.extend(
            [
                PersistentIdentifier.get("rn", rn)
                for rn in record.get("report_number", [])
            ]
        )
    except PIDDoesNotExistError:
        pass

    # Fetch deposit id from record and resolve deposit record and pid.
    depid = deposit_fetcher(None, record)
    if not depid:
        abort(404)

    is_project = is_project_record(record)

    deposit_cls = Project if is_project else Video
    depid, deposit = Resolver(
        pid_type=depid.pid_type,
        object_type="rec",
        getter=deposit_cls.get_record,
    ).resolve(depid.pid_value)

    pids.append(depid)

    form = RecordDeleteForm()
    form.standard_reason.choices = current_app.config["CDS_REMOVAL_REASONS"]
    form._id = pid
    if form.validate_on_submit():
        if form.confirm.data != str(pid.object_uuid):
            flash(
                "Incorrect record identifier (UUID): {}".format(form.confirm.data),
                category="error",
            )
        elif (
            is_project
            and not form.delete_videos.data
            and len(record.get("videos", [])) >= 0
        ):
            flash(
                'To delete a project with videos you must check the "Delete '
                'videos recursively" field.',
                category="error",
            )
        else:
            reason = (
                form.reason.data
                or dict(current_app.config["CDS_REMOVAL_REASONS"])[
                    form.standard_reason.data
                ]
            )
            pid_value = pid.pid_value
            delete_func = delete_project_record if is_project else delete_video_record
            report = delete_func(record.id, reason=reason, hard=form.hard_delete.data)
            flash(
                "Record {} and linked objects successfully deleted. "
                "See report for details.".format(pid_value),
                category="success",
            )
            return render_template(
                "cds_records/records_delete_report.html", report=report
            )

    return render_template(
        "cds_records/record_delete.html",
        form=form,
        pid=pid,
        pids=pids,
        record=record,
        deposit=deposit,
        is_project=is_project,
    )
