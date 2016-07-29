# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""E2E integration tests."""

from __future__ import absolute_import, print_function

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def test_search(live_server, env_browser, demo_records):
    """Test the search page and results."""
    env_browser.get(
        url_for('cds_home.index', _external=True)
    )

    WebDriverWait(env_browser, 120).until(
        EC.presence_of_all_elements_located(
            (By.CLASS_NAME, 'cds-home-input'))
    )
    # Search bar
    search_input = env_browser.find_element_by_name('q')
    search_input.send_keys('')
    search_input.send_keys(Keys.RETURN)

    # Expect the following facets
    expected_titles = ['Authors', 'Languages', 'Topic']

    WebDriverWait(env_browser, 120).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, '//invenio-search-facets//div[@class="panel-heading"]'))
    )

    if env_browser.find_elements_by_tag_name('invenio-search-range'):
        WebDriverWait(env_browser, 120).until(
            EC.presence_of_all_elements_located(
                (By.XPATH,
                 '//invenio-search-range//div[@class="panel-heading"]'))
        )
        expected_titles.insert(0, 'Year')

    # It should have four different facets
    facets = env_browser.find_elements_by_class_name('panel-heading')
    assert len(facets) == len(expected_titles)

    for index, title in enumerate(expected_titles):
        assert title == facets[index].text

    # It should have the sorting option `Control number` selected
    sort_by = Select(
        env_browser.find_element_by_name('select-')
    )
    assert sort_by.first_selected_option.text == 'Control number'

    # The first page should be selected
    pagination = env_browser.find_element_by_class_name('pagination')
    pagination_items = pagination.find_elements_by_tag_name('li')
    pagination_first_page = pagination_items[2]
    assert 'disabled' in pagination_items[0].get_attribute('class')
    assert 'active' in pagination_items[1].get_attribute('class')

    # Lets change page
    pagination_second_page = pagination_items[-1]
    pagination_second_page.find_element_by_tag_name('a').click()

    # Wait a bit
    env_browser.implicitly_wait(10)

    # Refresh the items
    pagination = env_browser.find_element_by_class_name('pagination')
    pagination_items = pagination.find_elements_by_tag_name('li')

    # Check the pagination status
    assert 'active' in pagination_items[2].get_attribute('class')
    assert 'active' not in pagination_items[-1].get_attribute('class')
