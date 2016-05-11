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
    'selenium>=2.48.0,<2.53.0',
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

setup_requires = [
    'Babel>=1.3',
    'setuptools>=20.6.7',
    'pytest-runner>=2.7.0',
]

install_requires = [
    'CairoSVG>=1.0.20',
    'Flask-BabelEx>=0.9.2',
    'Flask-Debugtoolbar>=0.10.0',
    'Flask-IIIF>=0.1.0',
    'cds-dojson>=0.3.1',
    'datacite>=0.2.1',
    'dcxml>=0.1.0',
    'idutils>=0.1.1',
    'invenio-access>=1.0.0a4',
    'invenio-accounts>=1.0.0a10',
    'invenio-admin>=1.0.0a3',
    'invenio-assets>=1.0.0a4',
    'invenio-base>=1.0.0a6',
    'invenio-db[postgresql,versioning]>=1.0.0a9',
    'invenio-celery>=1.0.0a4',
    'invenio-config>=1.0.0a1',
    'invenio-files-rest>=1.0.0a1',
    'invenio-formatter>=1.0.0a2',
    'invenio-i18n>=1.0.0a4',
    'invenio-indexer>=1.0.0a3',
    'invenio-jsonschemas>=1.0.0a3',
    'invenio-logging>=1.0.0a2',
    'invenio-mail>=1.0.0a3',
    # 'invenio-marc21>=1.0.0a2',
    'invenio-migrator[loader]>=1.0.0a2',
    'invenio-oaiserver>=1.0.0a4',
    'invenio-oauthclient>=1.0.0a2',
    'invenio-pages>=1.0.0a2',
    'invenio-pidstore>=1.0.0a7',
    'invenio-previewer>=1.0.0a2',
    'invenio-query-parser>=0.6.0',
    'invenio-records-rest>=1.0.0a10',
    'invenio-records-ui>=1.0.0a6',
    'invenio-records[postgresql]>=1.0.0a15',
    'invenio-rest[cors]>=1.0.0a7',
    'invenio-search-ui>=1.0.0a4',
    'invenio-search>=1.0.0a7',
    'invenio-theme>=1.0.0a11',
    'invenio-userprofiles>=1.0.0a5',
    'jsonref>=0.1',
    'marshmallow>=2.5.0',
    'Pillow>=3.2.0',
    'python-slugify>=1.2.0',
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
            'cds_theme_css = cds.modules.theme.bundles:css',
            'cds_theme_js = cds.modules.theme.bundles:js',
            'cds_record_js = cds.modules.records.bundles:js',
        ],
        'invenio_base.apps': [
            'cds_main_fixtures = cds.modules.fixtures:CDSFixtures',
            'flask_debugtoolbar = flask_debugtoolbar:DebugToolbarExtension',
        ],
        'invenio_base.blueprints': [
            'cds_home = cds.modules.home.views:blueprint',
            'cds_records = cds.modules.records.views:blueprint',
            'cds_search_ui = cds.modules.search_ui.views:blueprint',
            'cds_theme = cds.modules.theme.views:blueprint',
        ],
        'invenio_i18n.translations': [
            'messages = cds',
        ],
        'invenio_search.mappings': [
            'records = cds.modules.records.mappings',
        ],
        'invenio_jsonschemas.schemas': [
            'marc21 = dojson.contrib.marc21.schemas',
            'cds_marc21 = cds_dojson.marc21.schemas',
        ]
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
