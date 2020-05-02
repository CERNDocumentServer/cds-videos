# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2020 CERN.
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


"""Invenio-Flow is a module for managing simple backend workflows."""

FLOW_FACTORIES = {}
"""Define your application flows and options for them.

The structure of the dictionary is as follows:

.. code-block:: python

    def build_flow(flow):
        flow.chain(t1)
        flow.group(t2, [{'param': 'value}, {'param': 'value}])
        flow.chain([t3, t4])
        return flow


    def flow_permission_factory(action):
        def allow(*args, **kwargs):
            def can(self):
                return True
            return type('MyPermissionChecker', (), {'can': can})()

        def deny(*args, **kwargs):
            def can(self):
                return False
            return type('MyPermissionChecker', (), {'can': can})()

        def task_actions(flow, task_id):
            return allow()

        def flow_create(flow_name, payload):
            return allow()

        def flow_actions(flow, payload=None):
            return allow()

        _actions = {
            'flow-create': flow_create,
            'flow-status': flow_actions,
            'flow-start': flow_actions,
            'flow-restart': flow_actions,
            'flow-stop': flow_actions,
            'flow-task-start': task_actions,
            'flow-task-restart': task_actions,
            'flow-task-stop': task_actions,
        }

        return _actions.get(action, deny)


    FLOW_FACTORIES = {
        'my-flow-name': {
            'flow_imp': build_flow,
            'permission_factory_imp': flow_permission_factory
        },
        ...
    }
"""
