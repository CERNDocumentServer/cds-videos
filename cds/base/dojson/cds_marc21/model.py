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

from dojson.overdo import Overdo
from dojson.contrib.marc21 import marc21

class CDSMarc21(Overdo):

    """Translation Index for CDS specific MARC21."""

    def __init__(self):
        """Constructor.

        Initializes the list of rules with the default ones from doJSON.
        """
        super(CDSMarc21, self).__init__()
        self.rules.extend(marc21.rules)


cds_marc21 = CDSMarc21()
