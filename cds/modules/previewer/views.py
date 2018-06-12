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

"""CDS Previewer."""

from __future__ import absolute_import, print_function

from flask import Blueprint, abort, current_app, request
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag

from invenio_previewer.proxies import current_previewer
from invenio_previewer.api import PreviewFile

from .api import CDSPreviewDepositFile, CDSPreviewRecordFile
from .extensions import default


blueprint = Blueprint(
    'cds_previewer',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def preview_recid(pid, record, template=None, **kwargs):
    """Preview file for given record."""
    return preview(pid, record, preview_file_class=CDSPreviewRecordFile)


def preview_depid(pid, record, template=None, **kwargs):
    """Preview file for given deposit."""
    return preview(pid, record, preview_file_class=CDSPreviewDepositFile,
                   previewer='cds_deposit_video')


def preview_recid_embed(pid, record, template=None, **kwargs):
    """Return embedded player for video file."""
    return preview(pid, record, preview_file_class=CDSPreviewRecordFile,
                   previewer='cds_embed_video')


def preview(pid, record, **kwargs):
    """Preview file."""
    # Get filename from request parameters
    filename = request.view_args.get(
        'filename', request.args.get('filename', type=str))

    if not filename:
        # Get filename from 'preview' tag
        bucket_id = record['_buckets']['deposit']
        obj = ObjectVersion.get_by_bucket(
            bucket_id
        ).join(ObjectVersion.tags).filter(
            ObjectVersionTag.key == 'preview'
        ).one_or_none()

        if obj is None:
            abort(404)

        filename = obj.key

    return _try_previewers(pid, record, filename, **kwargs)


def _try_previewers(pid, record, filename, preview_file_class=PreviewFile,
                    previewer=None, **kwargs):
    """Try previewing file with all available previewers."""
    # Get file from record
    fileobj = current_previewer.record_file_factory(pid, record, filename)

    if not fileobj:
        abort(404)

    # Try to see if specific previewer is requested?
    file_previewer = previewer or fileobj.get('previewer')

    fileobj = preview_file_class(pid, record, fileobj)

    # Try out available previewers
    for plugin in current_previewer.iter_previewers(
            previewers=[file_previewer] if file_previewer else None):
        if plugin.can_preview(fileobj):
            try:
                return plugin.preview(fileobj, embed_config=request.args)
            except Exception:
                current_app.logger.warning(
                    ('Preview failed for {key}, in {pid_type}:{pid_value}'
                     .format(key=fileobj.file.key,
                             pid_type=fileobj.pid.pid_type,
                             pid_value=fileobj.pid.pid_value)),
                    exc_info=True)
    return default.preview(fileobj)
