# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2012, 2013, 2014, 2015 CERN.
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

"""Statistics Flask Blueprint."""

from flask import Blueprint, g, render_template, request

from flask_menu import register_menu

from invenio_base.i18n import _

from invenio_records.views import request_record


always = lambda: True

blueprint = Blueprint(
    'statistics', __name__, url_prefix="/record", template_folder='templates',
    static_folder='static'
)


@blueprint.route('/<int:recid>/statistics', methods=['GET'])
@request_record
@register_menu(blueprint, 'record.statistics', _('Statistics'), order=9,
               endpoint_arguments_constructor=lambda:
               dict(recid=request.view_args.get('recid')),
               visible_when=always)
def files(recid):
    """Return overview of attached files."""
    return render_template('statistics/page_views.html')
