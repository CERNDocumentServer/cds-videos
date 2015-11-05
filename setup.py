# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""CDS, Access articles, reports and multimedia content in HEP.

Links
-----
* `website <http://cds.cern.ch/>`_
* `development version <https://github.com/CERNDocumentServer/cds>`_
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os
import sys

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'isort>=4.2.2',
    'pep257>=0.7.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-pep8>=1.0.6',
    'pytest>=2.8.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.3',
    ],
    'development': [
        "Flask-DebugToolbar>=0.9",
        'setuptools-bower>=0.2'
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=1.3',
]

install_requires = [
    'Flask-BabelEx>=0.9.2',
    'Flask-IIIF>=0.1.0',
    'invenio-accounts>=1.0.0.dev20150000',
    'invenio-assets>=0.1.0.dev20150000',
    'invenio-base>1.0.0a1,<=1.0.0a2',
    'invenio-celery>=0.1.0.dev20150000',
    'invenio-config>=0.1.0.dev20150000',
    'invenio-db>=1.0.0a2',
    'invenio-i18n>=0.1.0.dev20150000',
    'invenio-mail>=1.0.0.dev20150000',
    'invenio-pidstore>=1.0.0a1',
    'invenio-records-rest>=1.0.0a2',
    'invenio-records-ui>=1.0.0a1',
    'invenio-records>=1.0.0a3',
    'invenio-theme>=0.1.0.dev20150000',
    'invenio[full]==3.0.0a1',
    'mixer>=4.9.5,<4.9.6',
    'six>=1.10',
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

# loads __version__
g = {}
with open(os.path.join("cds", "version.py"), "rt") as fp:
    exec(fp.read(), g)
version = g["__version__"]

setup(
    name='CDS',
    version=version,
    url='http://cds.cern.ch/',
    license='GPLv3',
    author='CERN',
    author_email='cds.support@cern.ch',
    description='Access articles, reports and multimedia content in HEP',
    long_description=__doc__,
    packages=packages,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
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
    entry_points={
        'console_scripts': [
            'cds = cds.cli:cli',
        ],
        'invenio_assets.bundles': [
            'cds_theme_css = cds.modules.theme.bundles:css',
            'cds_theme_js = cds.modules.theme.bundles:js',
            'cds_theme_home_js = cds.modules.theme.bundles:home',
        ],
        'invenio_base.blueprints': [
            'cds_theme = cds.modules.theme.views:blueprint',
        ],
        'invenio_i18n.translations': [
            'messages = cds',
        ],
    },
    cmdclass={'test': PyTest},
)
