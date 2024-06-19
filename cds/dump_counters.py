import requests
import json
from time import sleep
from elasticsearch import Elasticsearch
import datetime


class bcolors:
    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    ENDC = "\033[0m"


class VideosStatisticsType:
    MEDIA_VIEWS = "events.cds_videos_media_view"
    PAGE_VIEWS = "events.cds_videos_pageviews"
    MEDIA_DOWNLOADS = "events.cds_videos_media_download"


# new_es_url = "https://os-cds-apps-qa.cern.ch:443/os"
# new_es_auth = ('cds', 'TODO')
# cacert_path = "/etc/pki/tls/certs/CERN-bundle.pem"
CFG_ELASTICSEARCH_HOSTS = [{"host": "127.0.0.1", "port": 9199}]
es_client = Elasticsearch(CFG_ELASTICSEARCH_HOSTS)


def fetch_and_process_data_per_type(year, type):
    index = "cds-%s" % year
    print(
        bcolors.WARNING
        + "Processing data from %s" % index
        + " for event type %s" % type
        + bcolors.ENDC
    )
    new_index = "cds-%s" % year  # TODO: change this accordingly
    try:
        page = es_client.count(new_index, params=dict(type=type))
    except Exception as e:
        print(
            bcolors.ERROR
            + "FAILED to start fetching data from index %s. Stopping the process."
            % index
            + bcolors.ENDC
        )
        raise e
    total = page["count"]
    process_batch(new_index, type, total)

    print(bcolors.WARNING + "[%s] Processed %s" % (index, total) + bcolors.ENDC)


def fetch_and_process_data(year):
    fetch_and_process_data_per_type(year, VideosStatisticsType.MEDIA_VIEWS)
    fetch_and_process_data_per_type(year, VideosStatisticsType.MEDIA_DOWNLOADS)
    fetch_and_process_data_per_type(year, VideosStatisticsType.PAGE_VIEWS)


def process_batch(index, type, count):
    # url = "%s/%s/_bulk" % (new_es_url, index)
    # headers = {"Content-Type": "application/json"}
    actions = []

    try:
        with open("/tmp/es/counters/%s_log_%s.txt" % (type, index), "w") as file:
            file.write(json.dumps(dict(event_type=type, count=count)))
    except Exception as e:
        print(e)


years = [
    "2004",
    "2018",
    "2016",
    "2014",
    # "2024",
    "2015",
    "2022",
    "2017",
    "2005",
    "2007",
    "2006",
    "2011",
    "2019",
    "2009",
    "2023",
    "2021",
    "2012",
    "2013",
    "2020",
    "2003",
    "2010",
    "2008",
]  # TODO: Adjust according to the actual data
for year in years:
    fetch_and_process_data(year)
    print(bcolors.SUCCESS + "Process finished succesfully" + bcolors.ENDC)
