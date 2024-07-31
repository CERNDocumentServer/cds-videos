# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2015, 2016, 2018 CERN.
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

"""Test announcements."""

from datetime import datetime, timedelta

from cds.modules.announcements.models import Announcement as Ann

announcements = {
    'everywhere': {
        'message': 'everywhere',
        'path': None,
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=1),
        'active': True
    },
    'with_end_date': {
        'message': 'with_end_date',
        'path': '/',
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=1),
        'end_date': datetime.now() + timedelta(days=1),
        'active': True
    },
    'deposit_only': {
        'message': 'deposit_only',
        'path': '/deposit',
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=1),
        'active': True
    },
    'sub_deposit_only': {
        'message': 'sub_deposit_only',
        'path': '/deposit/upload',
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=1),
        'active': True
    },
    'disabled': {
        'message': 'disabled',
        'path': None,
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=1),
        'active': False
    },
    'expired': {
        'message': 'expired',
        'path': None,
        'style': 'info',
        'start_date': datetime.now() - timedelta(days=2),
        'end_date': datetime.now() - timedelta(days=1),
        'active': True
    }
}


def test_get_with_path_date(db):
    """Test get first active with with path and date."""
    row = Ann(**announcements['everywhere'])
    db.session.add(row)
    row = Ann(**announcements['with_end_date'])
    db.session.add(row)
    row = Ann(**announcements['disabled'])
    db.session.add(row)
    db.session.commit()

    assert Ann.get_for('/').message == 'everywhere'
    assert Ann.get_for('/deposit').message == 'everywhere'


def test_get_with_specific_path_date(db):
    """Test get first active with specific path and date."""
    row = Ann(**announcements['disabled'])
    db.session.add(row)
    row = Ann(**announcements['deposit_only'])
    db.session.add(row)
    db.session.commit()

    assert Ann.get_for('/deposit').message == 'deposit_only'
    assert Ann.get_for('/deposit/other').message == 'deposit_only'
    assert Ann.get_for('/') is None
    assert Ann.get_for('/other') is None


def test_get_with_sub_path_date(db):
    """Test get first active with sub path and date."""
    row = Ann(**announcements['disabled'])
    db.session.add(row)
    row = Ann(**announcements['sub_deposit_only'])
    db.session.add(row)
    db.session.commit()

    assert Ann.get_for(
        '/deposit/upload').message == 'sub_deposit_only'
    assert Ann.get_for('/deposit') is None
    assert Ann.get_for('/') is None
    assert Ann.get_for('/other') is None


def test_get_future_date(db):
    """Test get first active with future date."""
    row = Ann(**announcements['expired'])
    db.session.add(row)
    row = Ann(**announcements['disabled'])
    db.session.add(row)
    row = Ann(**announcements['deposit_only'])
    db.session.add(row)
    db.session.commit()

    assert Ann.get_for('/') is None
    assert Ann.get_for('/other') is None
    assert Ann.get_for('/deposit').message == 'deposit_only'


def test_get_expired_disabled(db):
    """Test get first active with future date."""
    row = Ann(**announcements['expired'])
    db.session.add(row)
    row = Ann(**announcements['disabled'])
    db.session.add(row)
    db.session.commit()

    assert Ann.get_for('/') is None
    assert Ann.get_for('/other') is None
    assert Ann.get_for('/deposit') is None


def test_disable_expired(db):
    """Test clean up old announcement but still active."""
    row = Ann(**announcements['everywhere'])
    db.session.add(row)
    row = Ann(**announcements['expired'])
    db.session.add(row)
    row = Ann(**announcements['with_end_date'])
    db.session.add(row)
    row = Ann(**announcements['sub_deposit_only'])
    db.session.add(row)
    db.session.commit()

    assert Ann.query.filter(Ann.active.is_(True)).count() == 4

    Ann.disable_expired()

    assert Ann.query.filter(Ann.active.is_(True)).count() == 3
    anns = Ann.query.all()
    assert anns[0].message == 'everywhere'
    assert anns[1].message == 'with_end_date'
    assert anns[2].message == 'sub_deposit_only'
