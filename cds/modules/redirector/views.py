# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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

"""CDS redirector views."""

from __future__ import absolute_import, print_function

from flask import Blueprint, abort, current_app, redirect, request, url_for
from six.moves.urllib.parse import urlencode
from six.moves.urllib.parse import urlparse
from sqlalchemy.orm.exc import NoResultFound

from invenio_pidstore.models import PersistentIdentifier

from cds.modules.records.api import Record

blueprint = Blueprint(
    'cds_redirector',
    __name__,
    template_folder='templates',
    static_folder='static',
)

api_blueprint = Blueprint(
    'cds_api_redirector',
    __name__,
)


def recid_from_rn(report_number):
    """Retrieve a report number's corresponding record ID."""
    object_uuid = PersistentIdentifier.query.filter_by(
        pid_type='rn',
        pid_value=report_number
    ).one().object_uuid

    record = Record.get_record(object_uuid).replace_refs()
    videos = record.get('videos')
    if videos:
        return videos[0]['recid']
    return record.get('recid')


# /record/<pid_value>/embed/<filename>
# /video/<report_number>
@blueprint.route('/video/<report_number>', strict_slashes=False)
def video_embed_alias(report_number):
    """Redirect from the old video embed URL to the new one."""
    try:
        recid = recid_from_rn(report_number)
    except NoResultFound:
        abort(404)

    return redirect(url_for(
        'invenio_records_ui.recid_embed_default', pid_value=recid,
        **request.args), code=301)


# /record/<:id:>/export/drupal
# /api/mediaexport?id=<report_number>
@api_blueprint.route('/mediaexport', strict_slashes=False)
def drupal_export_alias():
    """Redirect from the old drupal export URL to the new one."""
    rn = request.args.get('id', '')

    try:
        recid = recid_from_rn(rn)
    except NoResultFound:
        abort(404)

    api_url = url_for('invenio_records_rest.recid_item', pid_value=recid,
                      _external=True)

    arg_name = current_app.config['REST_MIMETYPE_QUERY_ARG_NAME']
    format_param = {arg_name: 'drupal'}

    api_url += ('&' if urlparse(api_url).query else '?') + urlencode(
        format_param)

    return redirect(api_url, code=301)
