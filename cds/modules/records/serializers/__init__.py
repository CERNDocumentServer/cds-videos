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

from invenio_records_rest.serializers.datacite import DataCite31Serializer
from invenio_records_rest.serializers.response import record_responsify, \
    search_responsify
from invenio_records_rest.schemas import RecordSchemaJSONV1

from .drupal import DrupalSerializer
from .json import CDSJSONSerializer as JSONSerializer
from .schemas.datacite import DataCiteSchemaV1
from .smil import SmilSerializer
from .vtt import VTTSerializer

# Serializers
# ===========

#: CDS SMIL serializer version 1.0.0
smil_v1 = SmilSerializer()

#: CDS VTT serializer version 1.0.0
vtt_v1 = VTTSerializer()

#: Drupal JSON serializer
drupal_v1 = DrupalSerializer(RecordSchemaJSONV1)

#: DataCite serializer
datacite_v31 = DataCite31Serializer(DataCiteSchemaV1, replace_refs=True)

#: CDSDeposit serializer
cdsdeposit_json_v1 = JSONSerializer(RecordSchemaJSONV1, replace_refs=True)

#: CDS JSON serializer v1
json_v1 = JSONSerializer(RecordSchemaJSONV1, replace_refs=True)

# Records-REST response serializers
# =================================

#: SMIL record serializer for individual records.
smil_v1_response = record_responsify(smil_v1, 'application/smil')

#: VTT record serializer for individual records.
vtt_v1_response = record_responsify(vtt_v1, 'text/vtt')

#: Drupal record serializer for individual records.
drupal_v1_response = record_responsify(drupal_v1, 'application/json')

#: DataCite v3.1 record serializer for individual records.
datacite_v31_response = record_responsify(
    datacite_v31, 'application/x-datacite+xml')

#: CDSDeposit record serializer for individual records.
cdsdeposit_json_v1_response = record_responsify(cdsdeposit_json_v1,
                                                'application/json')

#: JSON response bundler
json_v1_response = record_responsify(json_v1, 'application/json')

json_v1_search = search_responsify(json_v1, 'application/json')
