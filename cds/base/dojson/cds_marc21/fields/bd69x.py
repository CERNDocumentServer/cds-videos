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

"""CDS special/custom tags."""

from dojson import utils

from ..model import cds_marc21


@cds_marc21.over('subject_indicator', '^69[07]C_')
@utils.for_each_value
def subject_indicator(self, key, value):
    """Subject Indicator."""
    return value.get('a')


@cds_marc21.over('observation', '^691__')
def observation(self, key, value):
    """Observation."""
    return value.get('a')


@cds_marc21.over('accelerator_experiment', '^693__')
@utils.for_each_value
@utils.filter_values
def accelerator_experiment(self, key, value):
    """Experiment."""
    return {
        'acelerator': value.get('a'),
        'experiment': value.get('e'),
        'facility': value.get('f'),
        'subfield_s': value.get('s'),
    }


@cds_marc21.over('classification_terms', '^694__')
@utils.for_each_value
@utils.filter_values
def classification_terms(self, key, value):
    """Classification terms."""
    return {
        'uncontrolled_term': value.get('a'),
        'institute': value.get('9'),
    }


@cds_marc21.over('thesaurus_terms', '^695__')
@utils.for_each_value
@utils.filter_values
def thesaurus_terms(self, key, value):
    """Thesaurus term."""
    return {
        'uncontrolled_term': value.get('a'),
        'institute': value.get('9'),
    }
