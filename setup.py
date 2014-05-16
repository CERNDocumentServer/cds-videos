## This file is part of Invenio.
## Copyright (C) 2013, 2014 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
CDS Demosite
----------------

CDS demosite repository.
"""
from setuptools import setup, find_packages
import os

def requirements():
    req = []
    dep = []
    for filename in ['requirements.txt']:
        with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
            for line in f.readlines():
                if line.startswith('#'):
                    continue
                if '://' in line:
                    dep.append(str(line[:-1]))
                else:
                    req.append(str(line))
    return req, dep

install_requires, dependency_links = requirements()

setup(
    name='CDS Demosite',
    version='1.9999-dev',
    url='http://cds.cern.ch',
    license='GPLv3',
    author='CERN',
    author_email='info@invenio-software.org',
    description='Digital library software',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=install_requires,
    dependency_links=dependency_links,
    entry_points={
        'invenio.config': [
            "cds = cds.config"
        ]
    }
)
