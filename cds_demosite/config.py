# -*- coding: utf-8 -*-
#
## This file is part of Invenio.
## Copyright (C) 2014 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""
CDS Configuration
-----------------

Instance independent configuration (e.g. which extensions to load) is defined
in ``cds.config'' while instance dependent configuration (e.g. database
host etc.) is defined in an optional ``cds.instance_config'' which
can be installed by a separate package.

This config module is loaded by the Flask application factory via an entry
point specified in the setup.py::

    entry_points={
        'invenio.config': [
            "cds_demosite = cds_demosite.config"
        ]
    },
"""

PACKAGES = [
    "cds_demosite.base",
    "cds_demosite.modules.*",
    "invenio.modules.*",
]

PACKAGES_EXCLUDE = []

try:
    from cds.instance_config import *  # noqa
except ImportError:
    pass
