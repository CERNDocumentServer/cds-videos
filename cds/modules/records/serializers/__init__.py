# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Record serialization."""

from __future__ import absolute_import, print_function

from .smil import SmilSerializer
from .vtt import VTTSerializer
from invenio_records_rest.serializers.response import record_responsify

# Serializers
# ===========
#: CDS SMIL serializer version 1.0.0
smil_v1 = SmilSerializer()

#: CDS VTT serializer version 1.0.0
vtt_v1 = VTTSerializer()

# Records-REST serializers
# ========================
#: SMIL record serializer for individual records.
smil_v1_response = record_responsify(smil_v1, 'application/smil')

#: VTT record serializer for individual records.
vtt_v1_response = record_responsify(vtt_v1, 'text/vtt')
