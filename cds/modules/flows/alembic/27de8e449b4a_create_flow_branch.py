#
# This file is part of Invenio.
# Copyright (C) 2020 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Create Flow table."""


# revision identifiers, used by Alembic.
revision = "27de8e449b4a"
down_revision = None
branch_labels = (u"invenio-flow",)
depends_on = "dbdbc1b19cf2"


def upgrade():
    """Upgrade database."""


def downgrade():
    """Downgrade database."""
