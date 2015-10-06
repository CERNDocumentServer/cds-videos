# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from pkg_resources import iter_entry_points

from dojson.contrib.marc21 import marc21
from dojson.overdo import Overdo


class CDSMarc21(Overdo):

    """Translation Index for CDS specific MARC21."""

    __query__ = '690C_.a:CERN'

    def over(self, name, *source_tags, **kwargs):
        """Register creator rule.

        :param kwargs:
            * override: boolean, overrides the rule if either the `name` or the
              regular expression in `source_tags` are equal to the current
              ones.
        """
        def override(rule):
            if name == rule[1][0]:
                return True
            for field in source_tags:
                if field == rule[0]:
                    return True
            return False

        if kwargs.get('override', False):
            self.rules[:] = [rule for rule in self.rules if not override(rule)]

        return super(CDSMarc21, self).over(name, *source_tags)


translation = CDSMarc21(bases=(marc21, ),
                        entry_point_group='dojson.contrib.cds.marc21')
