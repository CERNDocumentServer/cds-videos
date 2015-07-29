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
from cds.base.dojson.photo import marc21, tomarc21
from cds.base.dojson.photo.model import CDSPhotoMarc21


class CDSAlbumMarc21(Overdo):
    """Adds new fields specific for albums to photo overdo"""
    overwrite_rules = [
        '^774..'
    ]

    def __init__(self):
        super(CDSAlbumMarc21, self).__init__()
        self.rules.extend(
            CDSPhotoMarc21.filter_unecessary_rules(marc21.rules,
                                                   self.overwrite_rules)
        )


class CDSAlbumToMarc21(Overdo):
    """Adds new fields specific for albums to photo overdo"""
    overwrite_rules = [
        '^774..'
    ]

    def __init__(self):
        super(CDSAlbumToMarc21, self).__init__()
        self.rules.extend(
            CDSPhotoMarc21.filter_unecessary_rules(tomarc21.rules,
                                                   self.overwrite_rules)
        )

album_marc21 = CDSAlbumMarc21()
album_tomarc21 = CDSAlbumToMarc21()