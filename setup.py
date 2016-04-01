# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
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
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'isort>=4.2.2',
    'pydocstyle>=1.0.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-flask>=0.10.0',
    'pytest-pep8>=1.0.6',
    'pytest>=2.8.0',
    'selenium>=2.48.0,<2.53.0',
    'six>=1.10.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.3',
    ],
    'postgresql': [
        'invenio-db[postgresql]>=1.0.0a9',
    ],
    'mysql': [
        'invenio-db[mysql]>=1.0.0a9',
    ],
    'sqlite': [
        'invenio-db[versioning]>=1.0.0a9',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for name, reqs in extras_require.items():
    if name in ('postgresql', 'mysql', 'sqlite'):
        continue
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=1.3',
    # OMG & 3 LOLs \_(ツ)_/¯
    'setuptools==20.4',
    'psycopg2',
]

install_requires = [
    'dojson>=1.0.0',
    'Flask-BabelEx>=0.9.2',
    'Flask-Debugtoolbar>=0.10.0',
    'Flask-IIIF>=0.1.0',
    'idutils>=0.1.1',
    'invenio-access',
    'invenio-accounts==1.0.0a9',
    'invenio-admin',
    'invenio-assets',
    'invenio-base==1.0.0a6',
    'invenio-celery==1.0.0a4',
    'invenio-config',
    'invenio-files-rest',
    'invenio-formatter',
    'invenio-i18n',
    'invenio-indexer',
    'invenio-logging',
    'invenio-mail',
    'invenio-pages',
    'invenio-pidstore==1.0.0a7',
    'invenio-previewer',
    'invenio-records==1.0.0a12',
    'invenio-records-rest',
    'invenio-records-ui',
    'invenio-rest[cors]',
    'invenio-search==1.0.0a5',
    'invenio-search-ui',
    'invenio-theme==1.0.0a10',
    'invenio-userprofiles',
    'invenio>=3.0.0a1,<3.1.0',
]

packages = find_packages()


class PyTest(TestCommand):
    """PyTest Test."""

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        """Init pytest."""
        TestCommand.initialize_options(self)
        self.pytest_args = []
        try:
            from ConfigParser import ConfigParser
        except ImportError:
            from configparser import ConfigParser
        config = ConfigParser()
        config.read('pytest.ini')
        self.pytest_args = config.get('pytest', 'addopts').split(' ')

    def finalize_options(self):
        """Finalize pytest."""
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """Run tests."""
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

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
        'invenio_search.mappings': [
            'records = cds.modules.records.data',
        ],
        'invenio_i18n.translations': [
            'messages = cds',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPLv3 License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    cmdclass={'test': PyTest},
)
