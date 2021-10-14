from flask_login import current_user

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.records.permissions import DepositPermission


def can(user_id, flow, action, **kwargs):
    """Check flow permission."""
    record = None
    if flow:
        deposit_id = flow.payload['deposit_id']
        record = deposit_video_resolver(deposit_id).project
    return DepositPermission.create(
        record=record, action=action, user=current_user
    ).can()
