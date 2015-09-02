# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

import json
import re

from collections import defaultdict, namedtuple

from cds.base.dojson.album import album_to_json, album_to_marc21
from cds.base.dojson.photo import photo_to_json, photo_to_marc21
from cds.base.dojson.utils import for_each_squash

from cds_marc21 import to_cds_json, to_cds_marc21

from dojson.contrib.marc21.utils import create_record, split_blob


TranslatorTuple = namedtuple('TranslatorTuple', ['to_json', 'to_marc21'])

default_translator = TranslatorTuple(to_cds_json, to_cds_marc21)

record_type_map = defaultdict(lambda: default_translator)

record_type_map.update({
    'ALBUM': TranslatorTuple(album_to_json, album_to_marc21),
    'IMAGE': TranslatorTuple(photo_to_json, photo_to_marc21)
})


class Translator():
    def __init__(self, translate_method):
        self.translate_method = translate_method

    @staticmethod
    def get_translator_to_json(marc21_object):
        if marc21_object.get('999__') and marc21_object['999__'].get('a'):
            return record_type_map[marc21_object['999__']['a']].to_json
        if marc21_object.get('001'):
            return default_translator.to_json
        raise KeyError

    @staticmethod
    def get_translator_to_marc21(json_object):
        if json_object.get('record_type'):
            return record_type_map[json_object['record_type'][0].get(
                'record_type'
            )].to_marc21
        if json_object['control_number']:
            return default_translator.to_marc21

        raise KeyError

    @staticmethod
    def get_translator(obj):
        """Returns new translator object

        :param obj: dictionary of object to be translated
        :return: Translator object set up for translating given object
        """
        if isinstance(obj, list):
            obj = obj[0]
        try:
            translator = Translator.get_translator_to_marc21(obj)
        except (KeyError, TypeError):
            try:
                translator = Translator.get_translator_to_json(obj)
            except KeyError:
                import pdb
                pdb.set_trace()
                translator = default_translator

        return Translator(translator.do)

    def _translate(self, record):
        return self.translate_method(record)

    def translate(self, record):
        if isinstance(record, list):
            return map(self.translate, record)
        # translator = Translator.get_translator(record)
        return self._translate(record)

    @staticmethod
    def test_correctness(input_marc21, output_json):
        restored_input = translate(output_json)

        missed_keys_number = 0
        different_keys_number = 0
        restored_keys_number = len(restored_input)

        missed_keys = []
        different_keys = []
        similar_keys = set()

        def extract_indicators(tagkey, obj):
            try:
                ind_1 = obj.pop('$ind1', '_')
                ind_2 = obj.pop('$ind2', '_')
                if isinstance(ind_1, list):
                    ind_1 = ind_1[0]
                if isinstance(ind_2, list):
                    ind_2 = ind_2[0]
                return tagkey + ind_1 + ind_2
            except TypeError:
                import pdb
                pdb.set_trace()

        altered_restored_object = {}
        for key, value in restored_input.iteritems():
            if isinstance(value, dict):
                ind_key = extract_indicators(key, value)

            if isinstance(value, list):
                try:
                    ind_key = extract_indicators(key, value[0])
                    for val in value[1:]:
                        val.pop('$ind1', None)
                        val.pop('$ind2', None)
                except AttributeError:
                    ind_key = key

            altered_restored_object[ind_key] = value

            found_key = False
            for original_key in input_marc21.keys():
                if re.match(original_key, ind_key):
                    found_key = original_key
                    break

            if not found_key:
                missed_keys_number += 1
                missed_keys.append(ind_key)
                continue

            similar_keys.add(found_key)
            if ind_key in for_each_squashed:
                squashed = for_each_squash(lambda self, key, value:
                                           value)(None, ind_key,
                                                  input_marc21[found_key])
                if squashed != altered_restored_object[ind_key]:
                    different_keys_number += 1
                    different_keys.append((
                        {ind_key: altered_restored_object[ind_key]},
                        {found_key: input_marc21[found_key]}))
            else:
                if altered_restored_object[ind_key] != input_marc21[found_key]:
                    different_keys_number += 1
                    different_keys.append((
                        {ind_key: altered_restored_object[ind_key]},
                        {found_key: input_marc21[found_key]}))

        return {
            'input_keys_number': len(input_marc21.items()),
            'restored_keys_number': restored_keys_number,
            'missed_keys_number':
                missed_keys_number +
                len(input_marc21.items()) -
                restored_keys_number,
            'different_keys_number': different_keys_number,
            'missed_keys':
                missed_keys +
                list(set(input_marc21.keys()) - similar_keys),
            'different_keys': different_keys,
            'record_id': input_marc21['001'],
            'correct': (missed_keys_number + different_keys_number) == 0,
            'input': input_marc21,
            'reverted_input': altered_restored_object
        }


def translate(obj):
    return Translator.get_translator(obj).translate(obj)

# TODO this list should be empty. This is only for testing
ignored_list = [
    762434,     # doubled 999
    762458,     # doubled 999
    762459,     # doubled 999
    762460,     # doubled 999
    762465,     # doubled 999
    762469,     # doubled 999
    762682,     # doubled 999
    762687,     # doubled 999
    763506,     # doubled 999
    765895,     # doubled 999
    1768509,    # doubled 999
    1778433,    # doubled 999
    1793594,    # doubled 999
    1799853,    # doubled 999
    1799854,    # doubled 999
    1799855,    # doubled 999
    1799856,    # doubled 999
    1799857,    # doubled 999
    1799858,    # doubled 999
    1799859,    # doubled 999
    1799860,    # doubled 999
    1799861,    # doubled 999
    1799862,    # doubled 999
    1799863,    # doubled 999
    1802146,    # doubled 999
    1802147,    # doubled 999
    1802148,    # doubled 999
    1802149,    # doubled 999
    1802150,    # doubled 999
    1802954,    # doubled 999
    1803921,    # doubled 999
    1973345,    # doubled 999
    1974137,    # doubled 999
    2013324,    # doubled 999
    761015,     # double 'r' in 774

    2026864,    # 6531 additional subfield

    1793606,    # 690C additional subfield
    1793607,
    1793608,
    1798760,

    763668,
]

for_each_squashed = [
    '963__',
]


def test_batch(filepath, fileoutput):
    records = get_marc21_from_file(filepath)
    result = []

    counter = 0
    ignored = 0
    correct = 0
    for record in records:
        if int(record['001'][0]) in ignored_list:
            ignored += 1
            continue
        if counter % 1000 == 0:
            print 'Processed %s/%s' % (counter, len(records))
        counter += 1
        try:
            json_output = translate(record)
            partial_result = Translator.test_correctness(record, json_output)
            if not partial_result['correct']:
                result.append(partial_result)
            else:
                correct += 1
        except Exception, e:
            import traceback
            partial_result = {
                'correct': False,
                'exception': str(e),
                'record_id': record['001'],
                'traceback': traceback.format_exc().split('\n')
            }
            result.append(partial_result)

    print 'Correct: %s\nIgnored %s\nErrors %s' % \
          (correct, ignored, len(records) - correct - ignored)
    json_result = json.dumps(result, indent=4, sort_keys=True)
    with open(fileoutput, 'w') as fd:
        fd.write(json_result)


def translate_file(filepath):
    with open(filepath, 'r') as fd:
        return translate(fd.read())


def get_marc21_from_file(filepath):
    with open(filepath, 'r') as fd:
        return create_records_from_blob(fd.read())


def create_records_from_blob(blob):
    return [create_record(data) for data in split_blob(blob)]


def check_translation_from_file(marc21_filepath):
    """Checks translation on records stored in file

    :param marc21_filepath: file containing test records in marc21
    :return: list of results containing test information
    """
    with open(marc21_filepath, 'r') as fd:
        return check_translation(fd.read())


def check_translation(marc21_object):
    record = create_records_from_blob(marc21_object)[0]
    result = Translator.get_translator(record).translate(record)
    return Translator.test_correctness(record, result)
