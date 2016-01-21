cache: redis-server
indexer: elasticsearch --config=elasticsearch.yml --path.data="$VIRTUAL_ENV/var/data/elasticsearch"  --path.logs="$VIRTUAL_ENV/var/log/elasticsearch"
web: cds --debug run
worker: celery worker -A cds.celery -l INFO
workermon: flower --broker=redis://localhost:6379/1
