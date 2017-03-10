# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Records tasks."""

from __future__ import absolute_import, print_function

import json
import requests
from flask import current_app
from celery import shared_task
from requests.exceptions import RequestException
from invenio_indexer.api import RecordIndexer
from invenio_db import db

from .api import Keyword
from .search import KeywordSearch, query_to_objects


def _get_keywords_from_api(url):
    """Get keywords list from API."""
    request = requests.get(
        url, headers={'User-Agent': 'cdslabs'}).text
    return {k['id']: k['name'] for k in json.loads(request)['tags']}


def _update_existing_keywords(indexer, keywords_api, keywords_db):
    """Update existing keywords."""
    to_db = []
    to_update_index = []
    keywords_saved = {k['key_id']: k for k in keywords_db}
    keys_saved = keywords_saved.keys()
    # check loaded keywords against the keywords in the database
    for key_id, name in keywords_api.items():
        keyword = None

        if key_id not in keys_saved:
            # create a new keyword
            keyword = Keyword.create(
                data={'key_id': key_id, 'name': name, 'deleted': False})
        elif keywords_saved[key_id]['deleted'] is True:
            # restore keyword
            keywords_saved[key_id].update(name=name, deleted=False)
            keyword = keywords_saved[key_id]
        elif name != keywords_saved[key_id]['name']:
            # update a keyword
            keywords_saved[key_id]['name'] = name
            keyword = keywords_saved[key_id]

        if keyword:
            to_db.append(keyword)

    for keyword in to_db:
        keyword = keyword.commit()
        to_update_index.append(str(keyword.id))

    indexer.bulk_index(iter(to_update_index))


def _delete_not_existing_keywords(indexer, keywords_api, keywords_db):
    """Delete not existing keywords."""
    to_soft_delete = []
    keys_loaded = keywords_api.keys()
    # check if some keywords is deleted
    for keyword in keywords_db:
        if keyword['deleted'] is False and \
                keyword['key_id'] not in keys_loaded:
            # soft delete the key_id
            keyword['deleted'] = True
            keyword.commit()
            to_soft_delete.append(str(keyword.id))

    indexer.bulk_index(iter(to_soft_delete))


@shared_task(bind=True)
def keywords_harvesting(self, max_retries=5, countdown=5):
    """Harvest all keywords."""
    try:
        # load from remote API the up-to-date list of keywords
        keywords_api = _get_keywords_from_api(
            url=current_app.config['CDS_KEYWORDS_HARVESTER_URL'])

        # load the list of keywords in the database
        keywords_db = query_to_objects(
            query=KeywordSearch().params(version=True), cls=Keyword)

        # index lists
        indexer = RecordIndexer()

        _update_existing_keywords(
            indexer=indexer, keywords_api=keywords_api, keywords_db=keywords_db
        )
        _delete_not_existing_keywords(
            indexer=indexer, keywords_api=keywords_api, keywords_db=keywords_db
        )

        db.session.commit()
    except RequestException as exc:
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=exc)
