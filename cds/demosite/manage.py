# -*- coding: utf-8 -*-
#
## This file is part of CDS.
## Copyright (C) 2015 CERN.
##
## CDS is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## CDS is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS. If not, see <http://www.gnu.org/licenses/>.
##
## In applying this licence, CERN does not waive the privileges and immunities
## granted to it by virtue of its status as an Intergovernmental Organization
## or submit itself to any jurisdiction.

"""Perform CDS demosite operations."""

from __future__ import print_function

import os
import pkg_resources
import sys

from invenio.ext.script import Manager

manager = Manager(usage=__doc__)

option_yes_i_know = manager.option('--yes-i-know', action='store_true',
                                   dest='yes_i_know', help='use with care!')


@option_yes_i_know
def photos(yes_i_know=False):
    """Load CDS photo demorecords."""
    _make_upload('cds-photos.xml', 'Going to load demo photos.')


@option_yes_i_know
def populate(yes_i_know=False):
    """Load CDS general demorecords."""
    _make_upload('cds-demobibdata.xml')


def _make_upload(name, description="Going to load demo records"):
    """Upload the demodata from the given file.

    :param str name: the demodata file name
    :param str description: the user message
    """
    from invenio.utils.text import wrap_text_in_a_box, wait_for_user
    from invenio.config import CFG_PREFIX
    from invenio.modules.scheduler.models import SchTASK

    wait_for_user(wrap_text_in_a_box(
        "WARNING: You are going to override data in tables!"
    ))

    print(">>> {0}".format(description))
    xml_data = pkg_resources.resource_filename(
        'cds',
        os.path.join('demosite', 'data', name))

    job_id = SchTASK.query.count()

    for cmd in ["bin/bibupload -u admin -i %s" % (xml_data, ),
                "bin/bibupload %d" % (job_id + 1, ),
                "bin/bibindex -u admin",
                "bin/bibindex %d" % (job_id + 2,),
                "bin/bibindex -u admin -w global",
                "bin/bibindex %d" % (job_id + 3,),
                "bin/bibreformat -u admin -o HB",
                "bin/bibreformat %d" % (job_id + 4,),
                "bin/webcoll -u admin",
                "bin/webcoll %d" % (job_id + 5,),
                ]:
        cmd = os.path.join(CFG_PREFIX, cmd)
        if os.system(cmd):
            print("ERROR: failed execution of", cmd)
            sys.exit(1)
    print(">>> CDS Demo records loaded successfully.")


def main():
    """Execute manager."""
    from invenio.base.factory import create_app
    app = create_app()
    manager.app = app
    manager.run()

if __name__ == '__main__':
    main()
