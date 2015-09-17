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

DEFAULT_SETTINGS = dict(
    home=[
       {'type': 'record_list',
        'title': '... from CERN Experiments',
        'collection': 'CERN Experiments',
        'query': ''},
       {'type': 'record_list',
        'title': '... published in CERN Bulletin',
        'collection': 'News Articles',
        'query': ''},
       {'type': 'record_list',
        'title': 'Latest books in CERN Library',
        'collection': 'Books',
        'query': ''},
       {'type': 'record_list',
        'title': 'Photos taken at CERN',
        'collection': 'Photos',
        'query': ''},
       {'type': 'record_list',
        'title': 'The Administrative Documents',
        'collection': 'CERN Administrative Documents',
        'query': ''},
       {'type': 'record_list',
        'title': '... from the LHC accelerator',
        'collection': 'LHC',
        'query': ''},
    ],
)
