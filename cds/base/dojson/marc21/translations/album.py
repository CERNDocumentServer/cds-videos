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

from .default import (CDSMarc21, translation as marc21)


class CDSAlbum(CDSMarc21):

    """Translation Index for CDS Albums."""

    __query__ = '999__.a:ALBUM'

    def __init__(self):
        """Constructor.

        Initializes the list of rules with the default ones
        from doJSON + CDSMarc21.
        """
        super(CDSAlbum, self).__init__()
        self.rules.extend(marc21.rules)

translation = CDSAlbum()
