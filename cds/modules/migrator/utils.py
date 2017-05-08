# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2017 CERN.
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
"""Migration utils."""

from flask import current_app


def process_fireroles(fireroles):
    """Extract firerole definitions."""
    rigths = set()
    for firerole in fireroles:
        for (allow, not_, field, expressions_list) in firerole[1]:
            if not allow:
                current_app.logger.warning(
                    'Not possible to migrate deny rules: {0}.'.format(
                        expressions_list))
                continue
            if not_:
                current_app.logger.warning(
                    'Not possible to migrate not rules: {0}.'.format(
                        expressions_list))
                continue
            if field in ('remote_ip', 'until', 'from'):
                current_app.logger.warning(
                    'Not possible to migrate {0} rule: {1}.'.format(
                        field, expressions_list))
                continue
            # We only deal with allow group rules
            for reg, expr in expressions_list:
                if reg:
                    current_app.logger.warning(
                        'Not possible to migrate groups based on regular'
                        ' expressions: {0}.'.format(expr))
                    continue
                clean_name = expr[
                    :-len(' [CERN]')].lower().strip().replace(' ', '-')
                rigths.add('{0}@cern.ch'.format(clean_name))
    return rigths


def update_access(data, *access):
    """Merge access rights information.

    :params data: current JSON structure with metadata and potentially an
        `_access` key.
    :param *access: List of dictionaries to merge to the original data, each of
        them in the form `action: []`.
    """
    current_rules = data.get('_access', {})
    for a in access:
        for k, v in a.items():
            current_x_rules = set(current_rules.get(k, []))
            current_x_rules.update(v)
            current_rules[k] = list(current_x_rules)

    data['_access'] = current_rules
