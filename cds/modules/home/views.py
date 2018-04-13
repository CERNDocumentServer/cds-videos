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

"""CDS Home UI."""

from __future__ import absolute_import, print_function

from flask import Blueprint, render_template
from flask_babelex import lazy_gettext as _
from flask_menu import current_menu

from invenio_cache.decorators import cached_unless_authenticated

blueprint = Blueprint(
    'cds_home',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@blueprint.before_app_first_request
def init_menu():
    """Initialize menu before first request."""
    item = current_menu.submenu('main.deposit')
    item.register(
        'invenio_deposit_ui.index',
        _('Upload'),
        order=2,
    )


@blueprint.route('/')
@cached_unless_authenticated(timeout=600, key_prefix='homepage')
def index():
    """CDS home page."""
    return render_template(
        'cds_home/home.html'
    )


@blueprint.route('/ping', methods=['HEAD', 'GET'])
def ping():
    """Ping blueprint used by loadbalancer."""
    return 'You Know, the CERN Document Server'
