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

import re

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def test_search_params(live_server, env_browser, demo_records):
    """Test the search page and results."""
    env_browser.get(
        url_for('cds_home.index', _external=True)
    )

    # Search bar
    search_val = 'a'

    WebDriverWait(env_browser, 120).until(
        EC.presence_of_all_elements_located(
            (By.CLASS_NAME, 'cds-home-input'))
    )

    search_input = env_browser.find_element_by_name('q')
    search_input.send_keys(search_val)
    search_input.send_keys(Keys.RETURN)

    subject_path = '//h3[text()="topic"]/../..//li'

    WebDriverWait(env_browser, 120).until(
        EC.presence_of_all_elements_located((By.XPATH, subject_path))
    )

    env_browser.implicitly_wait(10)
    current_search = env_browser.find_elements_by_xpath(
        '//invenio-search-bar//input[@type="text"]')[0].get_attribute('value')

    # Same value was searched
    assert search_val == current_search

    # Get first listed subject
    subject_item = env_browser.find_elements_by_xpath(subject_path)[0]
    subject = re.search(r' *(.*) \(\d*\) *', subject_item.text).group(1)

    # Filter results by subject
    subject_item.find_elements_by_tag_name('input')[0].click()

    # Filtered results have this subject
    assert all(subject in result.text for result in
               env_browser.find_elements_by_class_name('cds-media-subject'))

    result_link = env_browser.find_elements_by_xpath(
        '//h4[contains(@class, "cds-media-title")]/a')[0]
    result_title = result_link.text.strip()
    result_summary = env_browser.find_elements_by_xpath(
        '//div[contains(@class, "cds-media-summary")]/p')[0].text.strip()

    # Select the first result
    result_link.click()

    # Detail view must have the same title as the result
    assert result_title in env_browser.find_elements_by_class_name(
        'cds-record-detail-title')[0].text

    # Detail view must have the same summary as the result
    assert result_summary in env_browser.find_elements_by_xpath(
        '//dt[contains(., "Summary")]/following-sibling::dd')[0].text
