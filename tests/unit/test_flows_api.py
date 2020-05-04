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


"""Python basic API tests."""

from __future__ import absolute_import, print_function

from cds.modules.flows import Flow, task
from cds.modules.flows.models import Task


def test_basic_flow_api_usage(db):
    """Test basic flow creation."""

    @task
    def t1(common, **kwargs):
        """Task with an important mission."""
        # if common == 'common-arg':
        #     raise Exception()
        print('Run t1', common, kwargs)

    @task
    def t2(p, **kwargs):
        """Task with an even more important mission."""
        if p == 't2_1':
            # This one doesn't actually run anything, we just return
            return 'No need to run for {}'.format(p)

        # Do important stuff when required
        print('Run t2', p, kwargs)

    @task
    def t3(**kwargs):
        """Task with a secret mission."""
        print('Run t3', kwargs)

    @task(bind=True, max_retries=None)
    def t4(self, times, **kwargs):
        """Run this one n times."""
        print('Run t4: ', times, kwargs)
        if times > 0:
            self.commit_status(
                kwargs['task_id'], message='Running for {}'.format(times)
            )
            # Testing message updates
            t = Task.get(kwargs['task_id'])
            assert t.status.value == 'PENDING'
            assert t.message == 'Running for {}'.format(times)
            f = Flow.get_flow(kwargs['flow_id'])
            assert f.status['status'] == 'PENDING'

            # Reschedule the task to mimic breaking long standing tasks
            times = times - 1
            self.retry(args=(times,), kwargs=kwargs)

    flow = Flow.create('test', payload=dict(common='common-arg'))
    flow_id = flow.id
    assert flow.status['status'] == 'PENDING'

    # build the workflow
    def build(flow):
        flow.chain(t1)
        flow.group(t2, [{'p': 't2_1'}, {'p': 't2_2'}])
        flow.chain(t3, {'p': 't3'})
        flow.chain(t4, {'times': 10})

    flow.assemble(build)

    # Save tasks and flow before running
    db.session.commit()

    assert flow.status['status'] == 'PENDING'

    flow.start()

    flow = Flow.get_flow(flow_id)
    assert flow.status['status'] == 'SUCCESS'

    task_status = flow.status['tasks'][0]
    assert task_status['status'] == 'SUCCESS'
    flow_task_status = flow.get_task_status(task_status['id'])
    assert flow_task_status['status'] == 'SUCCESS'

    # Create a new instance of the same flow (restart)
    old_flow_id = flow_id
    flow = flow.__class__.create(
        flow.name, payload={'common': 'test 2'}, previous_id=old_flow_id
    )
    flow_id = flow.id
    assert flow.status['status'] == 'PENDING'
    flow.assemble(build)

    # Save tasks and flow before running
    db.session.commit()

    assert flow.status['status'] == 'PENDING'

    flow.start()

    assert flow_id != old_flow_id

    flow = Flow.get_flow(flow_id)
    assert str(flow.previous_id) == old_flow_id

    # Restart task
    flow.restart_task(task_status['id'])
    flow_task_status = flow.get_task_status(task_status['id'])
    assert flow_task_status['status'] == 'SUCCESS'
