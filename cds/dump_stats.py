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


def handle_retries(scroll_id, scroll_time):
    max_retries = (60 / 1) * 12  # Total retries for 12 hours every 1 minute
    retry_interval = 60  # 1 minute in seconds
    for _ in range(max_retries):
        print(
            bcolors.ERROR
            + "Fetching data failed. Sleeping for %s before re-trying." % retry_interval
            + bcolors.ENDC
        )
        sleep(retry_interval)
        try:
            page = es_client.scroll(scroll_id=scroll_id, scroll=scroll_time)
            return page
        except Exception as e:
            continue
    raise Exception("Failed to fetch data after multiple retries.")


def fetch_and_process_data_per_type(year, type):
    index = "cds-%s" % year
    print(
        bcolors.WARNING
        + "Processing data from %s" % index
        + " for event type %s" % type
        + bcolors.ENDC
    )
    new_index = "cds-%s" % year  # TODO: change this accordingly
    size = 1000
    batch = 0
    processed = 0
    scroll_time = "1h"
    try:
        page = es_client.search(
            index=index,
            doc_type=type,
            scroll=scroll_time,
            size=size,
            body={"query": {"match_all": {}}},
        )
    except Exception as e:
        print(
            bcolors.ERROR
            + "FAILED to start fetching data from index %s. Stopping the process."
            % index
            + bcolors.ENDC
        )
        raise e
    scroll_id = page["_scroll_id"]
    hits = page["hits"]["hits"]
    total = page["hits"]["total"]
    process_batch(new_index, type, hits)
    batch += 1
    if size * batch < total:
        processed = size * batch
    else:
        processed = total
    print(
        bcolors.WARNING
        + "[%s] Processed %s/%s" % (index, processed, total)
        + bcolors.ENDC
    )

    while True:
        try:
            page = es_client.scroll(scroll_id=scroll_id, scroll=scroll_time)
        except Exception as e:
            page = handle_retries(scroll_id, scroll_time)
        scroll_id = page["_scroll_id"]
        hits = page["hits"]["hits"]
        if not hits:
            print("Last result found: ", page)
            print(bcolors.SUCCESS + " Finished processing %s" % str(size * batch))
            if size * batch < total:
                print(
                    bcolors.ERROR + "Missed documents %s" % str(total - (size * batch))
                )
                with open("/tmp/es/failed_indices.txt", "a") as file:
                    file.write("Failed index %s" % index + " and type %s" % type)
            break
        process_batch(new_index, type, hits)

        batch += 1
        if size * batch < total:
            processed = size * batch
        else:
            processed = total

        print(
            bcolors.WARNING
            + "[%s] Processed %s/%s" % (index, processed, total)
            + bcolors.ENDC
        )

    print(bcolors.WARNING + "[%s] Clearing the scroll context." % index + bcolors.ENDC)
    es_client.clear_scroll(scroll_id=scroll_id)


def fetch_and_process_data(year):
    fetch_and_process_data_per_type(year, VideosStatisticsType.MEDIA_VIEWS)
    fetch_and_process_data_per_type(year, VideosStatisticsType.MEDIA_DOWNLOADS)
    fetch_and_process_data_per_type(year, VideosStatisticsType.PAGE_VIEWS)


def convert_to_epoch_millis_if_needed(input_str, _id, index):
    # Try to detect if the input string is already an epoch timestamp in milliseconds
    try:
        # Attempt to convert to an integer, successful conversion suggests it might be a Unix timestamp
        epoch_millis = int(input_str)
        # Optional: Check if the Unix timestamp is within a reasonable range, assuming it's milliseconds
        test_date = datetime.datetime.fromtimestamp(epoch_millis / 1000.0)
        if datetime.datetime(1970, 1, 1) <= test_date <= datetime.datetime.now():
            return epoch_millis
    except ValueError:
        # If it's not a valid integer, assume it's a datetime string
        pass

    # If it's a datetime string, parse it
    try:
        date_format = "%Y-%m-%dT%H:%M:%S"
        datetime_obj = datetime.datetime.strptime(input_str, date_format)
        epoch_millis = int(
            (datetime_obj - datetime.datetime(1970, 1, 1)).total_seconds() * 1000
        )
        return epoch_millis
    except ValueError:
        with open("/tmp/es/error_log_date_%s.txt" % index, "a") as file:
            file.write("\n%s" % _id.encode("utf-8"))


def transform_data(doc, index):
    doc["_source"]["event_type"] = doc.pop("_type", None)
    doc["_source"]["timestamp"] = convert_to_epoch_millis_if_needed(
        doc["_source"].pop("@timestamp", 0), doc["_id"], index
    )

    return doc["_source"]


def encode_dict(input_dict):
    encoded_dict = {}
    for key, value in input_dict.iteritems():
        # Encode the key
        encoded_key = key.encode("utf-8") if isinstance(key, unicode) else key

        # Recursively encode the value if it's a dictionary, else encode the value
        if isinstance(value, dict):
            encoded_value = encode_dict(value)
        elif isinstance(value, unicode):
            encoded_value = value.encode("utf-8")
        else:
            encoded_value = value

        encoded_dict[encoded_key] = encoded_value
    return encoded_dict


def process_batch(index, type, batch):
    # url = "%s/%s/_bulk" % (new_es_url, index)
    # headers = {"Content-Type": "application/json"}
    actions = []

    try:
        for doc in batch:
            action = {"index": {"_id": doc["_id"]}}
            try:
                transformed_doc = transform_data(doc, index)
                actions.append(json.dumps(action))
                actions.append(json.dumps(transformed_doc))
            except:
                print(bcolors.ERROR + "Failed to transform doc %s" % doc)

        bulk_data = "\n".join(actions) + "\n"
        with open("/tmp/es/%s_log_%s.txt" % (type, index), "a") as file:
            file.write(bulk_data)
    except Exception as e:
        pass


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
