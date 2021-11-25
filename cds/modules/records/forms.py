# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2019 CERN.
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

"""Forms for record module."""

from __future__ import absolute_import, print_function

from flask_babelex import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import (BooleanField, SelectField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import InputRequired


def strip_filter(text):
    """Filter for trimming whitespace."""
    return text.strip() if text else text


class RecordDeleteForm(FlaskForm):
    """Form for deleting a record."""

    reason = TextAreaField(
        _("Removal reason (custom)"),
        description=_(
            "Please provide a reason for removing the record. This reason will"
            " be displayed on the record tombstone page."
        ),
        filters=[strip_filter],
    )

    standard_reason = SelectField(
        _("Removal reason (standard options)"),
        coerce=str,
    )

    delete_videos = BooleanField(
        _("Delete videos recursively?"),
        default=False,
        description=_(
            "All videos attached to this project will be deleted too."
        ),
    )

    hard_delete = BooleanField(
        _("Remove completely the record? (AKA Hard delete)"),
        default=False,
        description=_(
            "All will be removed, versions, files, PIDs, dental records... "
            "Recovery of any kind will not be possible."
        ),
    )

    confirm = StringField(
        _("Confirm deletion"),
        [
            InputRequired(),
        ],
        description=_(
            "Please manually type the record identifier (UUID) in order to "
            "confirm the deletion."
        ),
    )

    delete = SubmitField(_("Permanently delete record"))
