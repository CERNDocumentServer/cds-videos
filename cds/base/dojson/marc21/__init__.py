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

from flask import current_app

from invenio.utils.datastructures import SmartDict

from invenio_search.api import Query

from .registry import translations as _translations


def convert_cdsmarcxml(source):
    """Convert CDS to JSON."""
    from dojson.contrib.marc21.utils import create_record, split_blob

    for data in split_blob(source.read()):
        record = create_record(data)
        yield query_matcher(record).do(record)


def query_matcher(record):
    """Record query matcher.

    :param record: :func:`dojson.contrib.marc21.utils.create_record` object.

    :returns: a translation instance
    :rtype: :class:`~cds.base.dojson.marc21.translations.default.CDSMarc21`
    """
    from cds.base.dojson.marc21.translations.default import (
        translation as marc21_default_translation
    )

    _smart_dict_record = SmartDict(dict(record))
    _matches = []
    for name, translation in _translations.iteritems():
        translation_query = translation.__query__
        query = Query(translation_query)

        if query.match(_smart_dict_record):
            current_app.logger.info(
                "Model `{0}` found matching the query {1}.".format(
                    name, translation_query
                )
            )
            _matches.append([name, translation])

    try:
        if len(_matches) > 1:
            current_app.logger.error(
                ("Found more than one matches `{0}`, now it'll fallback to {1}"
                 " for record {2}.").format(
                    _matches, _matches[0], _smart_dict_record
                )
            )
        return _matches[0][1]
    except IndexError:
        current_app.logger.error(
            "Model *not* found fallback to default {0}".format(
                _smart_dict_record
            )
        )
        return marc21_default_translation
