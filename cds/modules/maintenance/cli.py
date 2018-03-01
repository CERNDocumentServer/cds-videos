# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Fixture Modules."""

from __future__ import absolute_import, print_function

import click
from cds_sorenson.api import get_all_distinct_qualities
from click import ClickException
from flask.cli import with_appcontext

from cds.modules.maintenance.subformats import create_all_missing_subformats, \
    create_all_subformats, create_subformat


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@click.group()
def subformats():
    """Slaves command line utilities."""


@subformats.command()
@click.option('--recid', 'recid', default=None)
@click.option('--depid', 'depid', default=None)
@with_appcontext
def missing(recid, depid):
    """Create missing subformats given a record id or deposit id."""
    if not recid and not depid:
        raise ClickException('Missing option "--recid" or "--depid"')

    value = recid or depid
    type = 'recid' if recid else 'depid'
    output = create_all_missing_subformats(id_type=type, id_value=value)
    if output:
        click.echo("Creating the following subformats: {0}".format(output))
    else:
        click.echo("No missing format to create")


@subformats.group()
def recreate():
    """Recreate subformats for a video."""


@recreate.command()
@click.argument('quality')
@click.option('--recid', 'recid', default=None)
@click.option('--depid', 'depid', default=None)
@with_appcontext
def quality(recid, depid, quality):
    """Recreate subformat for the given quality."""
    if not recid and not depid:
        raise ClickException('Missing option "--recid" or "--depid"')

    value = recid or depid
    type = 'recid' if recid else 'depid'

    qualities = get_all_distinct_qualities()
    if quality not in qualities:
        raise ClickException(
            "Input quality must be one of {0}".format(qualities))

    output = create_subformat(id_type=type, id_value=value, quality=quality)
    if output:
        click.echo("Creating the following subformat: {0}".format(output))
    else:
        click.echo("This subformat cannot be transcoded.")


@recreate.command()
@click.option('--recid', 'recid', default=None)
@click.option('--depid', 'depid', default=None)
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Do you really want to recreate all subformats?')
@with_appcontext
def all(recid, depid):
    """Recreate all subformats."""
    if not recid and not depid:
        raise ClickException('Missing option "--recid" or "--depid"')

    value = recid or depid
    type = 'recid' if recid else 'depid'

    output = create_all_subformats(id_type=type, id_value=value)
    click.echo("Creating the following subformats: {0}".format(output))
