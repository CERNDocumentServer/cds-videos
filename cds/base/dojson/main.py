# This is just a WIP file and won't be included
# in the final version

import json
import sys
import traceback
import re
from dojson.contrib.marc21.utils import create_record, split_blob

from cds.base.dojson.photo import marc21, tomarc21
from cds.base.dojson.album import album_marc21, album_tomarc21

def translate_marc_to_json(marc_file, album=False, test=False):
    blob = [create_record(data) for data in split_blob(marc_file)]

    if album:
        parsed_record = [album_marc21.do(data) for data in blob]
    else:
        parsed_record = [marc21.do(data) for data in blob]

    if test:
        for xml_input, json_output in zip(blob, parsed_record):
            json_string = json.dumps(json_output)
            reverted_translation = translate_json_to_marc(json_string, album)[0]

            missed_keys_number = 0
            different_keys_number = 0
            reverted_keys_number = len(reverted_translation)

            missed_keys = []
            different_keys = []
            similar_keys = set()
            for key, value in reverted_translation.iteritems():
                if key not in xml_input.keys():
                    missed_keys_number += 1
                    missed_keys.append(key)
                    continue

                similar_keys.add(key)
                if reverted_translation[key] != xml_input[key]:
                    different_keys_number += 1
                    different_keys.append((reverted_translation[key], xml_input[key]))

            print "="*40
            print "Original number of entries: {0}".format(len(xml_input.items()))
            print "Reverted number of entries: {0}".format(reverted_keys_number)
            print "Missed keys: {0}".format(missed_keys_number + len(xml_input.items()) - reverted_keys_number)
            print "Different keys: {0}".format(different_keys_number)
            print "="*40
            print "Missed keys: " + str(missed_keys + list(set(xml_input.keys()) - similar_keys))
            print "Different keys:\n" + '\n'.join([str(key_pair) for key_pair in different_keys])
            print "="*40

    return parsed_record


def translate_json_to_marc(json_file, album=False, test=False):
    loaded_json = json.loads(json_file)
    if isinstance(loaded_json, dict):
        loaded_json = [loaded_json]
    if album:
        parsed_record = [album_tomarc21.undo(data) for data in loaded_json]
    else:
        parsed_record = [tomarc21.undo(data) for data in loaded_json]
    return parsed_record


def main_command(to_json=True):
    is_album = False

    filepath = sys.argv[1]

    if len(sys.argv) == 3:
        album_param = sys.argv[2]
        if album_param == '-a':
            is_album = True

    try:
        with open(filepath, 'r') as fd:
            if to_json:
                parsed_records = translate_marc_to_json(fd.read(), is_album, True)
            else:
                parsed_records = translate_json_to_marc(fd.read(), is_album)
            # print(json.dumps(parsed_records, indent=4, sort_keys=True))
    except:
        traceback.print_exc()


# def main():
#
#     filepaths = sys.argv[2:]
#     album_id = sys.argv[1]
#     for filepath in filepaths:
#         out_filepath = filepath[:filepath.rfind('.')] + '.json'
#
#         try:
#             parsed_record = translate_marc_to_json(open(out_filepath).read())
#             with open(os.path.join(OUT_DIRECTORY, os.path.basename(out_filepath)), 'w') as fd:
#                 fd.write(json.dumps(parsed_record, indent=4, sort_keys=True))
#         except Exception, e:
#             traceback.print_exc()
#             import pdb
#             pdb.set_trace()


if __name__=='__main__':
    # main()
    main_command()