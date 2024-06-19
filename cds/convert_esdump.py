import json
import datetime


def convert_to_epoch_millis_if_needed(input_str):
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
    date_format = "%Y-%m-%dT%H:%M:%S"
    datetime_obj = datetime.datetime.strptime(input_str, date_format)
    epoch_millis = int(
        (datetime_obj - datetime.datetime(1970, 1, 1)).total_seconds() * 1000
    )
    return epoch_millis


def process_type_one(record, outfile):
    # Process the first type of entry
    index_line = {"index": {"_id": record["_id"]}}
    outfile.write(json.dumps(index_line) + "\n")

    source = record["_source"]
    transformed_record = {
        "id_bibrec": source["id_bibrec"],
        "event_type": record["_type"],
        "level": source["level"],
        "visitor_id": source["visitor_id"],
        "unique_session_id": source["unique_session_id"],
        "bot": source["bot"],
        "timestamp": convert_to_epoch_millis_if_needed(source["@timestamp"]),
    }
    outfile.write(json.dumps(transformed_record) + "\n")


def process_type_two(record, outfile):
    # Process the second type of entry
    index_line = {"index": {"_id": record["_id"]}}
    outfile.write(json.dumps(index_line) + "\n")

    source = record["_source"]
    transformed_record = {
        "recid": source["recid"],
        "event_type": record["_type"],
        "level": source["level"],
        "visitor_id": source["visitor_id"],
        "unique_session_id": source["unique_session_id"],
        "format": source["format"],
        "external": source["external"],
        "file": source["file"],
        "type": source["type"],
        "timestamp": convert_to_epoch_millis_if_needed(source["@timestamp"]),
    }
    outfile.write(json.dumps(transformed_record) + "\n")


def convert_file(input_filename, output_filename):
    with open(input_filename, "r") as infile, open(output_filename, "w") as outfile:
        for line in infile:
            record = json.loads(line)

            # Identify and process the type of entry
            if record["_type"] == "events.cds_videos_pageviews":
                process_type_one(record, outfile)
            elif record["_type"] == "events.cds_videos_media_view":
                process_type_two(record, outfile)


if __name__ == "__main__":
    input_filename = "/Users/zzacharo/projects/cds-videos/tmp/es/script_indices/esdump_events.cds_videos_media_view-2023.txt"  # Replace with your input file path
    output_filename = (
        "tmp/es/script_indices/events.cds_videos_media_view_log_cds-2023.txt"  #
    )
    convert_file(input_filename, output_filename)
