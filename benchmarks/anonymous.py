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

"""Anonymous benchmarks."""

from __future__ import absolute_import, print_function

from locust import HttpLocust, TaskSet, task


class AnonymousWebsiteTasks(TaskSet):
    """Benchmark anonymous user."""

    base_url = 'https://videos.cern.ch/'

    @task
    def download(self):
        """Task download."""
        self.client.get(
            self.base_url + 'api/files/0a5b827f-29a8-4a9a-975e-25fd7699e097/'
            'posterframe.jpg?versionId=02f67d4c-2753-4258-9a1d-82fd21150935')

    @task
    def static(self):
        """Task static file."""
        self.client.get(
            self.base_url + 'static/gen/cds.0c24f045.css')

    @task
    def homepage(self):
        """Task home page."""
        self.client.get(self.base_url)

    @task
    def search(self):
        """Task search result."""
        self.client.get(self.base_url + 'search?page=1&size=20&q=')


class WebsiteUser(HttpLocust):
    """Locust.

    To run it, just `locust -f anonymous.py --host=https://videos.cern.ch` and
    open the browser `http://127.0.0.1:8089/`
    """

    task_set = AnonymousWebsiteTasks
    min_wait = 5000
    max_wait = 15000
