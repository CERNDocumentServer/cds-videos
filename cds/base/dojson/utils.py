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


def for_each_squash(f):
    @functools.wraps(f)
    def wrapper(self, key, values, **kwargs):
        if isinstance(values, list):
            unmerged_list = [f(self, key, value, **kwargs) for value in values]
            merged_dict = {}
            for unmerged_dict in unmerged_list:
                for key, element in unmerged_dict.iteritems():
                    if key in merged_dict:
                        if isinstance(merged_dict[key], list):
                            # already a list - append
                            merged_dict[key] += element
                        else:
                            # not a list - create one
                            merged_dict[key] = [merged_dict[key], element]
                    else:  # new key
                        merged_dict[key] = element
            return merged_dict
        return f(self, key, values, **kwargs)
    return wrapper
