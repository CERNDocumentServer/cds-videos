
from invenio_indexer.tasks import index_record


def _index_deposit(deposit):
    """Index deposit if set."""
    if deposit:
        index_record.delay(str(deposit.id))


def update_deposit_state(deposit_id=None):
    """Update deposit state on ElasticSearch."""
    from cds.modules.deposit.api import deposit_video_resolver
    if deposit_id:
        deposit_video = deposit_video_resolver(deposit_id)
        _index_deposit(deposit_video)
        _index_deposit(deposit_video.project)
