# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2019 CERN.
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

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, url_for)
from flask_security import current_user, login_required
from invenio_db import db
from invenio_records_ui.signals import record_viewed
from invenio_sequencegenerator.api import Sequence, Template

from ..records.permissions import (has_admin_permission,
                                   has_read_record_eos_path_permission)
from ..records.providers import CDSReportNumberProvider
from .api import CDSDeposit
from .form import ReserveReportNmberForm

blueprint = Blueprint(
    'cds_deposit',
    __name__,
    template_folder='templates',
    static_folder='static'
)


def project_view(pid, record, template=None, **kwargs):
    """Edit project view."""
    record_viewed.send(
        current_app._get_current_object(),
        pid=pid,
        record=record,
    )
    return render_template(
        template,
        pid=pid,
        record=record,
        record_type='project',
    )


@blueprint.app_template_filter()
def check_avc_permissions(record):
    """Check if user has permission to see EOS video library path."""
    return has_read_record_eos_path_permission(current_user, record)


@blueprint.app_template_global()
def has_avc_permission():
    """Test if current has has AVC permission."""
    return has_read_record_eos_path_permission(current_user, record=None)


@blueprint.app_template_filter()
def check_if_super_admin(record):
    """Check if user is super admin."""
    return has_admin_permission(current_user, record)


@blueprint.app_template_filter('tolinksjs')
def to_links_js(pid, deposit=None, dep_type=None):
    """Get API links."""
    if not isinstance(deposit, CDSDeposit):
        return []

    if dep_type:
        api_endpoint = current_app.config['DEPOSIT_RECORDS_API']
        self_url = api_endpoint.format(pid_value=pid.pid_value, type=dep_type)
    else:
        api_endpoint = current_app.config['DEPOSIT_RECORDS_API_DEFAULT']
        self_url = api_endpoint.format(pid_value=pid.pid_value)

    return {
        'self': self_url,
        'html': url_for(
            'invenio_deposit_ui.{}'.format(dep_type or pid.pid_type),
            pid_value=pid.pid_value),
        'bucket': current_app.config['DEPOSIT_FILES_API'] + '/{0}'.format(
            str(deposit.files.bucket.id)),
        'discard': self_url + '/actions/discard',
        'edit': self_url + '/actions/edit',
        'publish': self_url + '/actions/publish',
        'files': self_url + '/files',
    }


@blueprint.route('/deposits/reserve-rn', methods=['GET', 'POST'])
@login_required
def reserve_report_number():
    """Form to reserver a new report number."""
    if not has_read_record_eos_path_permission(current_user, None):
        abort(403)

    form = ReserveReportNmberForm()

    if form.validate_on_submit():
        data = form.data
        if not data.get('project_number'):
            # reserve project first
            project_counter = Sequence('project-v1_0_0', **data).next()
            CDSReportNumberProvider.create(
                object_type='rec',
                pid_value=project_counter
            )
        else:
            # Get the project template
            template = Template('project-v1_0_0')
            counter = template.model.counter(**data)
            project_counter =  counter.template_instance.format(
                counter=data['project_number'])

        video_sequence = Sequence(
            'video-v1_0_0', **{'project-v1_0_0': project_counter})
        video_counter = video_sequence.next()
        CDSReportNumberProvider.create(
            object_type='rec',
            pid_value=video_counter
        )
        flash('New report number reserved {0}.'.format(video_counter))

        db.session.commit()

        return redirect(url_for('invenio_deposit_ui.index'))


    return render_template(
        'cds_deposit/reserve_report_number.html', form=form)
