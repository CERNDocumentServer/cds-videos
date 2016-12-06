# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2015, 2016 CERN.
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

"""CDS, Access articles, reports and multimedia content in HEP.

Links
-----
* `website <http://cds.cern.ch/>`_
* `development version <https://github.com/CERNDocumentServer/cds>`_
"""

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'isort>=4.2.2',
    'mock>=1.3.0',
    'pydocstyle>=1.0.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-flask>=0.10.0',
    'pytest-pep8>=1.0.6',
    'pytest-runner>=2.7.0',
    'pytest>=2.8.0',
    'selenium>=2.53.6',
    'simplejson>=3.10',
    'six>=1.10.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.3',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for name, reqs in extras_require.items():
    extras_require['all'].extend(reqs)

# Do not include in all requirement
extras_require['xrootd'] = [
    'invenio-xrootd>=1.0.0a3',
    'xrootdpyfs>=0.1.3',
]

setup_requires = [
    'Babel>=1.3',
    'setuptools>=20.6.7',
    'pytest-runner>=2.7.0',
]

install_requires = [
    'arrow>=0.7.0',
    'CairoSVG>=1.0.20,<2.0.0',
    'Flask-Admin>=1.4.2',
    'Flask-BabelEx>=0.9.2',
    'Flask-Debugtoolbar>=0.10.0',
    'Flask-IIIF>=0.1.0',
    'Flask-WTF==0.13',
    'Flask>=0.11.1',
    'cds-dojson>=0.3.2',
    'datacite>=0.2.1',
    'dcxml>=0.1.0',
    'idutils>=0.2.3',
    'invenio-access>=1.0.0a9',
    'invenio-accounts>=1.0.0a16',
    'invenio-admin>=1.0.0a3',
    'invenio-assets>=1.0.0b2',
    'invenio-base>=1.0.0a14',
    'invenio-celery>=1.0.0a4',
    'invenio-communities>=1.0.0a13',
    'invenio-config>=1.0.0b1',
    'invenio-db[postgresql,versioning]>=1.0.0b2',
    'invenio-deposit>=1.0.0a6',
    'invenio-files-rest>=1.0.0a11',
    'invenio-formatter>=1.0.0a2',
    'invenio-i18n>=1.0.0b1',
    'invenio-indexer>=1.0.0a7',
    'invenio-jsonschemas>=1.0.0a3',
    'invenio-logging[sentry]>=1.0.0a3',
    'invenio-mail>=1.0.0a4',
    'invenio-migrator>=1.0.0a7',
    'invenio-oauth2server>=1.0.0a12',
    'invenio-oauthclient>=1.0.0a10',
    'invenio-pages>=1.0.0a3',
    'invenio-pidstore>=1.0.0a9',
    'invenio-previewer>=1.0.0a8',
    'invenio-query-parser>=0.6.0',
    'invenio-records-files>=1.0.0a7',
    'invenio-records-rest>=1.0.0a15',
    'invenio-records-ui>=1.0.0a7',
    'invenio-records[postgresql]>=1.0.0a17',
    'invenio-rest[cors]>=1.0.0a9',
    'invenio-search-ui>=1.0.0a5',
    'invenio-search>=1.0.0a7',
    # FIXME wait invenio-sse is released
    #  'invenio-sse>=1.0.0a1',
    'invenio-theme>=1.0.0a14',
    'invenio-userprofiles>=1.0.0a7',
    'invenio-webhooks>=1.0.0a4',
    'jsonref>=0.1',
    'jsonresolver>=0.2.1',
    'marshmallow>=2.5.0',
    'Pillow>=3.2.0',
    'pexpect>=4.2.1',
    'python-slugify>=1.2.0',
    'raven<=5.1.0',
    'requests>=2.10.0',
    'Wand>=0.4.2',
    'celery<4.0,>=3.1',                 # FIXME: invenio-indexer
    'elasticsearch<3.0.0,>=2.0.0',      # FIXME: invenio-search
    'elasticsearch-dsl<3.0.0,>=2.0.0',  # FIXME: invenio-search
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join("cds", "version.py"), "rt") as fp:
    exec(fp.read(), g)
    version = g["__version__"]

setup(
    name='CDS',
    version=version,
    description='Access articles, reports and multimedia content in HEP',
    long_description=readme + '\n\n' + history,
    license='GPLv3',
    author='CERN',
    author_email='cds.support@cern.ch',
    url='http://cds.cern.ch/',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'console_scripts': [
            'cds = cds.cli:cli',
        ],
        'invenio_assets.bundles': [
            'cds_deposit_jquery_js = cds.modules.deposit.bundles:js_jquery',
            'cds_deposit_js = cds.modules.deposit.bundles:js_deposit',
            'cds_previewer_theoplayer_css = cds.modules.previewer.bundles:theoplayer_css',
            'cds_previewer_theoplayer_js = cds.modules.previewer.bundles:theoplayer_js',
            'cds_previewer_video_css = cds.modules.previewer.bundles:video_css',
            'cds_previewer_video_js = cds.modules.previewer.bundles:video_js',
            'cds_record_js = cds.modules.records.bundles:js',
            'cds_theme_css = cds.modules.theme.bundles:css',
            'cds_theme_js = cds.modules.theme.bundles:js',
        ],
        'invenio_base.api_apps': [
            'cds_iiif = cds.modules.cds_iiif:CDSIIIF',
            #'cds_xrootd = cds.modules.xrootd:CDSXRootD',
        ],
        'invenio_base.apps': [
            'cds_main_fixtures = cds.modules.fixtures:CDSFixtures',
            'flask_debugtoolbar = flask_debugtoolbar:DebugToolbarExtension',
            #'cds_xrootd = cds.modules.xrootd:CDSXRootD',
            # FIXME should be move to invenio-webhooks
            'invenio_webhooks = invenio_webhooks:InvenioWebhooks',
        ],
        'invenio_base.blueprints': [
            'cds_deposit = cds.modules.deposit.views:blueprint',
            'cds_home = cds.modules.home.views:blueprint',
            'cds_previewer = cds.modules.previewer.views:blueprint',
            'cds_records = cds.modules.records.views:blueprint',
            'cds_search_ui = cds.modules.search_ui.views:blueprint',
            'cds_theme = cds.modules.theme.views:blueprint',
        ],
        'invenio_pidstore.fetchers': [
            'cds_catid = cds.modules.deposit.fetchers:catid_fetcher',
        ],
        'invenio_pidstore.minters': [
            'cds_recid = cds.modules.records.minters:recid_minter',
            'cds_catid = cds.modules.deposit.minters:catid_minter',
        ],
        'invenio_i18n.translations': [
            'messages = cds',
        ],
        'invenio_search.mappings': [
            'records = cds.modules.records.mappings',
            'deposits = cds.modules.deposit.mappings',
            'categories = cds.modules.deposit.mappings',
        ],
        'invenio_jsonschemas.schemas': [
            'marc21 = dojson.contrib.marc21.schemas',
            'cds = cds_dojson.schemas',
            'cds_deposit = cds.modules.deposit.jsonschemas',
        ],
        'invenio_celery.tasks': [
            'cds_celery_tasks = cds.modules.webhooks.tasks',
        ],
        'invenio_webhooks.receivers': [
            'avc = cds.modules.webhooks.receivers:AVCWorkflow',
            'downloader = cds.modules.webhooks.receivers:Downloader',
        ],
        'invenio_previewer.previewers': [
            'cds_video = cds.modules.previewer.extensions.video',
        ],
        'invenio_sse.integrations': [
            'deposit = invenio_sse.contrib.deposit.ext:InvenioSSEDeposit',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 2 - Pre-Alpha',
    ],
)
