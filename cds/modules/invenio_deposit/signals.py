# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Deposit module signals."""

from blinker import Namespace

_signals = Namespace()

post_action = _signals.signal("post-action")
"""Signal is sent after the REST action.

Kwargs:

#. action (str) - name of REST action, e.g. "publish".

#. pid (invenio_pidstore.models.PersistentIdentifier) - PID of the deposit.
        The pid_type is assumed to be 'depid'.

#. deposit (invenio_depost.api.Deposit) - API instance of the deposit

Example subscriber:

.. code-block:: python

    def listener(sender, action, pid, deposit):
        pass

    from ..invenio_deposit.signals import post_action
    post_action.connect(listener)
"""
