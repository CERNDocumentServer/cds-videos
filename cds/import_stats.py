import json
import requests
from datetime import datetime
from opensearchpy import OpenSearch, helpers
from time import sleep

# OpenSearch server URL
# OS_URL = "http://127.0.0.1:9200"
# auth = ("user", "password")

# Initialize the OpenSearch client
# os_client = OpenSearch(
#     OS_URL,
#     http_auth=auth,
#     use_ssl=True,  # set to True if your cluster is using HTTPS
#     verify_certs=False,  # set to False if you do not want to verify SSL certificates
#     ssl_show_warn=False,  # set to False to suppress SSL warnings)
# )
OS_URL = "http://127.0.0.1:9200"
os_client = OpenSearch(OS_URL)

# Input and output files
input_file_path = "./tmp/es/script_indices"

output_index = "cds-videos-prod-events-stats"

LEGACY_TO_INDEX_MAPPING = {
    "events.cds_videos_media_view": "media-record-view",
    "events.cds_videos_pageviews": "record-view",
    "events.cds_videos_media_download": "file-download",
}


class bcolors:
    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    ENDC = "\033[0m"


class LegacyToIndex:
    MEDIA_VIEWS = "media-record-view"
    PAGE_VIEWS = "record-view"
    MEDIA_DOWNLOADS = "file-download"


class VideosStatisticsType:
    MEDIA_VIEWS = "events.cds_videos_media_view"
    PAGE_VIEWS = "events.cds_videos_pageviews"
    MEDIA_DOWNLOADS = "events.cds_videos_media_download"


def drop_unknown_fields(entry, known_fields):
    """Drop any field that is not part of the known keys."""
    from copy import deepcopy

    _dict = deepcopy(entry)
    for key in _dict.keys():
        if key not in known_fields:
            entry.pop(key, None)


def process_media_record_view_and_download_entry(entry):
    # Convert timestamp to strict_date_hour_minute_second format
    timestamp = entry["timestamp"]
    entry["timestamp"] = datetime.utcfromtimestamp(timestamp / 1000).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    entry["updated_timestamp"] = entry["timestamp"]
    entry["file"] = entry.setdefault("file", "unknown")

    if "FOOTAGE" in entry["file"]:
        entry["type"] = "footage"
    else:
        entry["type"] = "video"

    # compute unique_id
    entry["unique_id"] = f"legacy_{entry['file']}"
    # cast recid to string
    recid = entry.get("recid")
    if recid is not None:
        entry["recid"] = str(entry["recid"])

    # keep only known fields
    KNOWN_KEYS = [
        "timestamp",
        "recid",
        "visitor_id",
        "format",
        "file",
        "type",
        "quality",
        "unique_id",
        "unique_session_id",
        "updated_timestamp",
    ]
    drop_unknown_fields(entry, KNOWN_KEYS)

    return entry


def process_page_view_entry(entry):
    # Convert timestamp to strict_date_hour_minute_second format
    timestamp = entry["timestamp"]
    entry["timestamp"] = datetime.utcfromtimestamp(timestamp / 1000).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    entry["updated_timestamp"] = entry["timestamp"]

    # Rename "bot" to "is_robot" and "id_bibrec" to "recid"
    entry["is_robot"] = entry.pop("bot", False)

    # Add pid_value, pid_type
    entry["pid_type"] = "recid"
    entry["pid_value"] = str(entry.get("id_bibrec", "unknown"))

    # We didn't keep the "record_id", so we replace with None
    entry["record_id"] = ""

    # compute unique_id
    entry["unique_id"] = f"{entry['pid_type']}_{entry['pid_value']}"

    # keep only known fields
    KNOWN_KEYS = [
        "timestamp",
        "record_id",
        "pid_type",
        "pid_value",
        "visitor_id",
        "is_robot",
        "unique_id",
        "unique_session_id",
        "updated_timestamp",
    ]
    drop_unknown_fields(entry, KNOWN_KEYS)

    return entry


def handle_bulk_retries(os_client, bulk_data):
    max_retries = (60 / 1) * 12  # Total retries for 12 hours every 1 minute
    retry_interval = 60  # 1 minute in seconds

    for _ in range(max_retries):
        print(
            bcolors.ERROR
            + "Failed to bulk upload data. Sleeping for %s before re-trying."
            % retry_interval
            + bcolors.ENDC
        )
        sleep(retry_interval)
        try:
            helpers.bulk(os_client, bulk_data)
            return
        except Exception as e:
            continue
    raise Exception("Failed to bulk upload data after multiple retries.")


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


def process_entry(entry):

    try:
        # Move event_type to a separate index (handled in bulk helper)
        event_type = entry.pop("event_type")

        if event_type == VideosStatisticsType.MEDIA_VIEWS:
            processed_entry = process_media_record_view_and_download_entry(entry)
            index_type = LegacyToIndex.MEDIA_VIEWS
        elif event_type == VideosStatisticsType.MEDIA_DOWNLOADS:
            processed_entry = process_media_record_view_and_download_entry(entry)
            index_type = LegacyToIndex.MEDIA_DOWNLOADS
        elif event_type == VideosStatisticsType.PAGE_VIEWS:
            processed_entry = process_page_view_entry(entry)
            index_type = LegacyToIndex.PAGE_VIEWS

        # Retrieve year and month from timestamp
        date_object = datetime.fromisoformat(processed_entry["timestamp"])
        year = f"{date_object.year:4}"
        month = f"{date_object.month:02}"
        return True, {
            "_op_type": "index",
            "_index": f"{output_index}-{index_type}-{year}-{month}",
            "_source": processed_entry,
        }
    except Exception as e:
        print(e)
        return None, entry


def main():
    # Read and process the dumped ES entries
    import os

    failed = []
    succeeded = []

    with open(f"./tmp/es/completed_to_index.txt", "r") as success_log:
        lines = success_log.readlines()
        for line in lines:
            succeeded.append(line.split("\n")[0])

    def is_file_empty(file_path):
        with open(file_path, "r") as file:
            for line in file:
                if line.strip():  # Check if the line is not empty or just whitespace
                    return False
        return True

    for root, _, files in os.walk(input_file_path):

        for file in files:
            file_path = os.path.join(root, file)
            try:
                if is_file_empty(file_path):
                    print(f"File {file_path} is empty. Continuing....")
                    continue
                if file_path in succeeded:
                    print(f"File {file_path} has already been indexed. Continuing....")
                    continue
            except:
                print("Failed to process ", file_path)
            print("Processing.....", file_path)
            with open(file_path, "r") as file:
                lines = file.readlines()

            actions = []
            for i in range(0, len(lines), 2):
                if len(lines) > i:
                    index_line = json.loads(lines[i])
                    data_line = json.loads(lines[i + 1])
                    status, action = process_entry(data_line)
                    if status is not None:
                        action["_id"] = index_line["index"]["_id"]
                        actions.append(action)
                    else:
                        failed.append(action)

            # Bulk import processed entries to OpenSearch
            print(f"Bulk indexing {len(actions)} entries from {file_path}")
            try:
                helpers.bulk(os_client, actions)
            except Exception as e:
                handle_bulk_retries(os_client, actions)

            with open(f"./tmp/es/completed_to_index.txt", "a+") as success_log:
                success_log.write(file_path)
                success_log.write("\n")

        with open(f"./tmp/es/failed_to_index.txt", "w+") as error_log:
            for item in failed:
                json.dump(item, error_log)
                error_log.write("\n")


if __name__ == "__main__":
    main()
