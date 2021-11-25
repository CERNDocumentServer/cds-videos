# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
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

"""CDS LDAP client."""
import ldap
from flask import current_app


class LdapClient(object):
    """Ldap client class for user importation/synchronization.

    Response example:
        [
            {'displayName': [b'Joe Foe'],
             'department': [b'IT/CDA'],
             'uidNumber': [b'100000'],
             'mail': [b'joe.foe@cern.ch'],
             'cernAccountType': [b'Primary'],
             'employeeID': [b'101010']
             'postOfficeBox': [b'JM12345']
            },...
        ]
    """

    LDAP_BASE = "OU=Users,OU=Organic Units,DC=cern,DC=ch"
    LDAP_EGROUP_BASE = "OU=e-groups,OU=Workgroups,DC=cern,DC=ch"

    LDAP_CERN_PRIMARY_ACCOUNTS_FILTER = "(&(cernAccountType=Primary))"

    LDAP_USER_RESP_FIELDS = [
        "mail",
        "displayName",
        "department",
        "cernAccountType",
        "employeeID",
        "uidNumber",
        "postOfficeBox",
        "cernInsitituteName",
        "givenName",
        "sn",
    ]

    LDAP_EGROUP_RESP_FIELDS = [
        "mail",
        "displayName",
    ]

    def __init__(self, ldap_url=None):
        """Initialize ldap connection."""
        ldap_url = ldap_url or current_app.config["CDS_LDAP_URL"]
        self.ldap = ldap.initialize(ldap_url)

    def _search_paginated_primary_account(self, page_control):
        """Execute search to get primary accounts."""
        return self.ldap.search_ext(
            self.LDAP_BASE,
            ldap.SCOPE_ONELEVEL,
            self.LDAP_CERN_PRIMARY_ACCOUNTS_FILTER,
            self.LDAP_USER_RESP_FIELDS,
            serverctrls=[page_control],
        )

    def search_user_by_email(self, email):
        """Query ldap to retrieve user by person id."""
        id_filter = "(&(cernAccountType=Primary)(mail={}*))"
        self.ldap.search_ext(
            self.LDAP_BASE,
            ldap.SCOPE_ONELEVEL,
            id_filter.format(email),
            self.LDAP_USER_RESP_FIELDS,
            serverctrls=[
                ldap.controls.SimplePagedResultsControl(
                    True, size=7, cookie=""
                )
            ],
        )

        res = self.ldap.result()[1]

        return [x[1] for x in res]

    def search_users_by_name(self, name):
        """Query ldap to retrieve user by person id."""
        name_filter = "(&(cernAccountType=Primary)(|(displayName=*{name})(displayName={name}*)))"

        self.ldap.search_ext(
            self.LDAP_BASE,
            ldap.SCOPE_ONELEVEL,
            name_filter.format(name=name),
            self.LDAP_USER_RESP_FIELDS,
            serverctrls=[
                ldap.controls.SimplePagedResultsControl(
                    True, size=7, cookie=""
                )
            ],
        )

        res = self.ldap.result()[1]

        return [x[1] for x in res]

    def search_egroup_by_email(self, email):
        name_filter = "(&(mail={email}*))"
        self.ldap.search_ext(
            self.LDAP_EGROUP_BASE,
            ldap.SCOPE_ONELEVEL,
            name_filter.format(email=email),
            self.LDAP_EGROUP_RESP_FIELDS,
            serverctrls=[
                ldap.controls.SimplePagedResultsControl(
                    True, size=7, cookie=""
                )
            ],
        )

        res = self.ldap.result()[1]

        return [x[1] for x in res]
