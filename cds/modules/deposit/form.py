# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2019 CERN.
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

"""Deposit extra forms."""


import arrow
from flask_wtf import FlaskForm as Form
from invenio_i18n import lazy_gettext as _
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_sequencegenerator.api import Template
from wtforms import IntegerField, SelectField, StringField, ValidationError, validators


class ReserveReportNumberForm(Form):
    """Reserver report number form."""

    year = StringField(
        label=_('Publication year'),
        description=_(
            'Publication year of the project/video.'
            'The current year will be used by default.'
        ),
        validators=[
            validators.regexp(
                r'\d{4}',
                message=_('The year must be entered with 4 digits, i.e. 1985'),
            )
        ],
        default=arrow.now().year,
    )

    category = SelectField(
        label=_('Category'),
        choices=[('CERN', 'CERN')],
        default='CERN',
        validators=[validators.DataRequired()],
    )

    type = SelectField(
        label=_('Type'),
        choices=[('FOOTAGE', 'FOOTAGE'), ('VIDEO', 'VIDEO')],
        validators=[validators.DataRequired()],
    )

    project_number = IntegerField(
        label=_('Project number'),
        description=_(
            'Optional. Enter project number (e.g. for CERN-VIDEO-001, enter '
            '001) or leave it empty if no project yet.'
        ),
        validators=[validators.optional()],
    )

    def validate_project_number(self, field):
        if not isinstance(field.data, int):
            return
        template = Template('project-v1_0_0')
        counter = template.model.counter(**self.data)
        project_rn = counter.template_instance.format(
            counter=field.data)
        try:
            PersistentIdentifier.get('rn', project_rn)
        except PIDDoesNotExistError:
            raise ValidationError("Not existent project number")


class MintReportNumber(Form):
    """Assign report number."""

    report_number = SelectField(
        label=_('Report Number'),
        description=_(
            'If you do not find you report number here it could be because you '
            ' did reserve it for a different category and/or type.'
        ),
        validators=[validators.DataRequired()],
    )
