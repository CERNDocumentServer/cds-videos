# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
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

"""Mysite Invenio API application."""

from invenio_base.app import create_app_factory
from invenio_base.wsgi import create_wsgi_factory
from invenio_config import create_conf_loader

from . import config

env_prefix = 'APP'

conf_loader = create_conf_loader(config=config, env_prefix=env_prefix)

create_api = create_app_factory(
    'cds',
    env_prefix=env_prefix,
    conf_loader=conf_loader,
    bp_entry_points=['invenio_base.api_blueprints'],
    ext_entry_points=['invenio_base.api_apps'],
)


create_app = create_app_factory(
    'cds',
    env_prefix=env_prefix,
    conf_loader=conf_loader,
    bp_entry_points=['invenio_base.blueprints'],
    ext_entry_points=['invenio_base.apps'],
    wsgi_factory=create_wsgi_factory({'/api': create_api})
)
