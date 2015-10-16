# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
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

from invenio_ext.assets import Bundle

js = Bundle(
    "js/personal_collection/init.js",
    output="personal-collections.js",
    weight=92,
    filters="requirejs",
    bower={
        # Personal collections
        "async": "~1.2.1",
        "depot": "~0.1.6",
        "lodash": "~3.9.3",
        "sortable.js": "~1.2.0",
    }
)
