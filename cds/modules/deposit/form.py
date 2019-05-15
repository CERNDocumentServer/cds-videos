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
from flask_babelex import gettext as _
from flask_wtf import Form
from wtforms import IntegerField, SelectField, StringField, validators


class ReserveReportNmberForm(Form):
    """Reserver report number form."""

    year = StringField(
        label=_('Publication year'),
        description=_(
            'Publication year of the project/video.'
            'The current year will be used by default.'
        ),
        validators=[
            validators.regexp(
                '\d{4}',
                message=_('The year must be entered with 4 digits, i.e. 1985')
            )
        ],
        default=arrow.now().year,
    )

    category = SelectField(
        label=_('Category'),
        choices=[('CERN', 'CERN')],
        default='CERN',
        validators=[validators.DataRequired()]
    )

    type = SelectField(
        label=_('Type'),
        choices=[('FOOTAGE', 'FOOTAGE'), ('VIDEO', 'VIDEO')],
        validators=[validators.DataRequired()]
    )

    project_number = IntegerField(
        label=_('Project number'),
        description=_('Optional. If your trying to reserve a report number for'
                      ' a video that belongs to an existing project, enter '
                      'the project\'s number, otherwise a new will be created'
        ),
        validators=[
            validators.optional(),
        ],
    )

    @property
    def data(self):
        """Form data."""
        d = super(ReserveReportNmberForm, self).data
        d.pop('csrf_token', None)
        return d
