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

"""CDS interface."""

from __future__ import absolute_import, print_function

from flask import Blueprint, current_app, url_for

from .api import CDSDeposit

blueprint = Blueprint(
    'cds_deposit',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@blueprint.app_template_filter('tolinksjs')
def to_links_js(pid, deposit=None):
    """Get API links."""
    if not isinstance(deposit, CDSDeposit):
        return []

    self_url = current_app.config['DEPOSIT_RECORDS_API'].format(
        pid_value=pid.pid_value)

    return {
        'self': self_url,
        'html': url_for(
            'invenio_deposit_ui.{}'.format(pid.pid_type),
            pid_value=pid.pid_value),
        'bucket': current_app.config['DEPOSIT_FILES_API'] + '/{0}'.format(
            str(deposit.files.bucket.id)),
        'discard': self_url + '/actions/discard',
        'edit': self_url + '/actions/edit',
        'publish': self_url + '/actions/publish',
        'files': self_url + '/files',
    }


@blueprint.app_template_filter('tofilesjs')
def to_files_js(deposit):
    """List files in a deposit."""
    if not isinstance(deposit, CDSDeposit):
        return []

    res = []

    for f in deposit.files:
        res.append({
            'key': f.key,
            'version_id': f.version_id,
            'checksum': f.file.checksum,
            'size': f.file.size,
            'completed': True,
            'progress': 100,
            'links': {
                'self': (
                    current_app.config['DEPOSIT_FILES_API'] +
                    u'/{bucket}/{key}?versionId={version_id}'.format(
                        bucket=f.bucket_id,
                        key=f.key,
                        version_id=f.version_id,
                    )),
            }
        })

    for f in deposit.multipart_files.all():
        res.append({
            'key': f.key,
            'size': f.size,
            'multipart': True,
            'completed': f.completed,
            'processing': True,
            'progress': 100,
            'links': {
                'self': (
                    current_app.config['DEPOSIT_FILES_API'] +
                    u'/{bucket}/{key}?uploadId={upload_id}'.format(
                        bucket=f.bucket_id,
                        key=f.key,
                        upload_id=f.upload_id,
                    )),
            }
        })

    return res
