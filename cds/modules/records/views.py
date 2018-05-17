# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
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
from flask import (Blueprint, current_app, make_response, render_template,
                   request)
from werkzeug.utils import import_string

blueprint = Blueprint(
    'cds_records',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def stats_recid(pid, record, template=None, **kwargs):
    """Preview file for given record."""
    return render_template(
        'cds_records/record_stats.html',
        record=record
    )


def records_ui_export(pid, record, template=None, **kwargs):
    """Export a record."""
    formats = current_app.config.get('CDS_RECORDS_EXPORTFORMATS')
    fmt = request.view_args.get('format')

    if formats.get(fmt) is None:
        return render_template(
            'cds_records/records_export_unsupported.html'), 410
    else:
        serializer = import_string(formats[fmt]['serializer'])
        data = serializer.serialize(pid, record)
        if 'raw' in request.args:
            response = make_response(data)
            response.headers['Content-Type'] = formats[fmt]['mimetype']
            return response
        else:
            if isinstance(data, six.binary_type):
                data = data.decode('utf8')

            return render_template(
                template,
                pid=pid,
                record=record,
                data=data,
                format_title=formats[fmt]['title']
            )
