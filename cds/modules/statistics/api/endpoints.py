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

from __future__ import absolute_import
from flask import Blueprint, render_template, request, Markup
import json
from functools import wraps
from flask_login import login_required

from . import elasticsearch

from invenio.config import CFG_ES_STATISTICS_INDEX_PREFIX
from ..config import STATS_CFG
from invenio.modules.access.engine import acc_authorize_action

api = Blueprint('statistics_api', __name__, url_prefix='/statistics/api')


def viewstatistics_only(f):
    @wraps(f)
    @login_required
    def _wrapped(*args, **kwargs):
        authorized, msg = acc_authorize_action(request, 'viewstatistics')
        if authorized != 0:
            return render_template('visualisations/403.html',
                                   message=Markup(msg)), 403
        return f(*args, **kwargs)
    return _wrapped


@api.route('/<name>/histogram', methods=['GET'])
@viewstatistics_only
@elasticsearch.histogram
def histogram(**kwargs):
    name = kwargs['name']
    event = STATS_CFG['events'][name]
    doc_type = event['params']['doc_type']
    del kwargs['name']
    return elasticsearch.get_histogram(doc_type=doc_type,
                                       **kwargs)


@api.route('/<name>/terms', methods=['GET'])
@viewstatistics_only
@elasticsearch.terms
def terms(**kwargs):
    name = kwargs['name']
    event = STATS_CFG['events'][name]
    doc_type = event['params']['doc_type']
    del kwargs['name']
    return elasticsearch.get_terms(doc_type=doc_type,
                                   **kwargs)