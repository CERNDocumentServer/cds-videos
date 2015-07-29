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
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Photo MARC 21 model definition."""
from dojson.overdo import Overdo
from dojson.contrib.marc21 import marc21 as generic_marc21
from dojson.contrib.marc21 import tomarc21 as generic_tomarc21


class CDSPhotoMarc21(Overdo):
    overwrite_rules = [
        '^856.[10_28]',
        'constituent_unit_entry'
    ]

    def __init__(self):
        super(CDSPhotoMarc21, self).__init__()
        self.rules.extend(self.filter_unecessary_rules(generic_marc21.rules, self.overwrite_rules))

    @staticmethod
    def filter_unecessary_rules(rules, overwrite_rules):
        """Filters out rules definied in overwrite_rules

        Function returns the rules list from parameter with
        overwrite_rules removed - overwrite_rules is the list
        of regexps or field names
        """
        return [rule for rule in rules if rule[0] not in overwrite_rules and rule[1][0] not in overwrite_rules]



class CDSPhotoToMarc21(Overdo):
    overwrite_rules = [
        '^856.[10_28]',
        'constituent_unit_entry'
    ]

    def __init__(self):
        super(CDSPhotoToMarc21, self).__init__()
        self.rules.extend(self.filter_unecessary_rules(generic_tomarc21.rules, self.overwrite_rules))

    @staticmethod
    def filter_unecessary_rules(rules, overwrite_rules):
        """Filters out rules definied in overwrite_rules

        Function returns the rules list from parameter with
        overwrite_rules removed - overwrite_rules is the list
        of regexps or field names
        """
        return [rule for rule in rules if rule[0] not in overwrite_rules and rule[1][0] not in overwrite_rules]


tomarc21 = CDSPhotoToMarc21()
marc21 = CDSPhotoMarc21()
