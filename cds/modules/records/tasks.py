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

from .api import Keyword, CDSRecord
from .search import KeywordSearch, query_to_objects
from .symlinks import SymlinksCreator


def _get_keywords_from_api(url):
    """Get keywords list from API."""
    request = requests.get(
        url, headers={'User-Agent': 'cdslabs'}).text

    keywords = {}
    for tag in json.loads(request)['tags']:
        keywords[tag['id']] = dict(
            name=tag['name'],
            provenance=url
        )
    return keywords


def _update_existing_keywords(indexer, keywords_api, keywords_db):
    """Update existing keywords."""
    def _keyword_data(values):
        """Prepare the keyword data."""
        return dict(
            name=values.get('name'),
            provenance=values.get('provenance', ''),
            deleted=values.get('deleted', False)
        )

    def _check_if_updated(old_keyword, new_data):
        """Return True in the keyword should be updated."""
        old_data = _keyword_data(old_keyword)
        return old_data != new_data

    to_db = []
    to_update_index = []
    keywords_saved = {k['key_id']: k for k in keywords_db}
    keys_saved = keywords_saved.keys()
    # check loaded keywords against the keywords in the database
    for key_id, values in keywords_api.items():
        keyword = None

        if key_id not in keys_saved:
            # create a new keyword
            data = _keyword_data(values)
            data.update(key_id=key_id)
            keyword = Keyword.create(data=data)
        elif _check_if_updated(keywords_saved[key_id], _keyword_data(values)):
            # update a keyword (also handles the restoring of a keyword)
            keywords_saved[key_id].update(_keyword_data(values))
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


@shared_task(ignore_result=True, default_retry_delay=10 * 60)
def create_symlinks(previous_record, record_uuid):
    """Create video symlinks."""
    record_new = CDSRecord.get_record(record_uuid)
    SymlinksCreator().create(previous_record, record_new)
