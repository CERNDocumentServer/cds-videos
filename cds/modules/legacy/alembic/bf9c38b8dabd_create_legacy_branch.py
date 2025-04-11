#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Create legacy branch"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf9c38b8dabd'
down_revision = None
branch_labels = ("legacy",)
depends_on = '35c1075e6360'


def upgrade():
    """Upgrade database."""
    pass


def downgrade():
    """Downgrade database."""
    pass
