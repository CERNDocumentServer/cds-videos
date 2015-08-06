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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

import functools

from collections import defaultdict


def for_each_squash(f):
    @functools.wraps(f)
    def wrapper(self, key, values, **kwargs):
        if not isinstance(values, list):
            return f(self, key, values, **kwargs)

        unmerged_list = [f(self, key, value, **kwargs) for value in values]
        merge_dict = defaultdict(list)

        for unmerged_dict in unmerged_list:
            for key, element in unmerged_dict.iteritems():
                merge_dict[key].append(element)

        merge_dict = {key: (value if len(value) > 1 else value[0])
                      for key, value in merge_dict.iteritems()}
        return merge_dict
    return wrapper
