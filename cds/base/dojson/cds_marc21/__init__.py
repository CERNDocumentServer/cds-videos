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


from .fields import (
    bd69x,
)
from .model import cds_marc21


def convert_cdsmarcxml(source):
    """Convert CDS MARC XML to JSON."""
    from dojson.contrib.marc21.utils import create_record, split_blob

    for data in split_blob(source.read()):
        yield cds_marc21.do(create_record(data))


__all__ = ('cds_marc21', 'convert_cdsmarcxml')
