# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Registry for personal collections."""

from flask_registry import RegistryProxy

from invenio_ext.registry import ModuleAutoDiscoverySubRegistry
from invenio_utils.datastructures import LazyDict


boxes_proxy = RegistryProxy('boxes', ModuleAutoDiscoverySubRegistry, 'boxes')


boxes = LazyDict(
    lambda: dict((module.box.__boxname__, (module.box))
                 for module in boxes_proxy if hasattr(module, 'box'))
)
