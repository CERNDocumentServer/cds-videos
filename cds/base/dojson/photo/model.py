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
from cds.base.dojson.cds_marc21 import to_cds_json, to_cds_marc21
from cds.base.dojson.cds_marc21.model import ToCDSMarc21, ToCDSJson


class PhotoToMarc21(ToCDSMarc21):
    def __init__(self):
        super(PhotoToMarc21, self).__init__()
        self.rules.extend(to_cds_marc21.rules)


class PhotoToJson(ToCDSJson):
    def __init__(self):
        super(PhotoToJson, self).__init__()
        self.rules.extend(to_cds_json.rules)


photo_to_marc21 = PhotoToMarc21()
photo_to_json = PhotoToJson()
