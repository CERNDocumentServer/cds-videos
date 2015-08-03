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

from collections import defaultdict, namedtuple

from dojson.contrib.marc21.utils import create_record, split_blob

from cds.base.dojson.album import album_to_json, album_to_marc21
from cds.base.dojson.photo import photo_to_json, photo_to_marc21
from cds_marc21 import to_cds_json, to_cds_marc21


TranslatorTuple = namedtuple('TranslatorTuple', ['to_json', 'to_marc21'])

default_translator = TranslatorTuple(to_cds_json, to_cds_marc21)

record_type_map = defaultdict(lambda: default_translator)

record_type_map.update({
    'ALBUM': TranslatorTuple(album_to_json, album_to_marc21),
    'IMAGE': TranslatorTuple(photo_to_json, photo_to_marc21)
})


class Translator():
    @staticmethod
    def get_translator_to_json(marc21_object):
        return record_type_map[marc21_object['999__']['a']].to_json

    @staticmethod
    def get_translator_to_marc21(json_object):
        return record_type_map[json_object['record_type']].to_marc21

    def _translate(self, translate_method, record):
        translated_record = translate_method(record)
        return translated_record

    def to_json(self, record):
        if isinstance(record, list):
            return map(self.to_json, record)
        translator = Translator.get_translator_to_json(record)
        return self._translate(translator.do, record)

    def to_marc21(self, json_object):
        if isinstance(json_object, list):
            return map(self.to_marc21, json_object)
        translator = Translator.get_translator_to_marc21(json_object)
        return self._translate(translator.undo, json_object)


def to_json(marc21_object):
    """Translates marc21 object (parsed, dict) to json"""
    translator = Translator()
    return translator.to_json(marc21_object)


def to_marc21(json_object):
    """Translates json (dict) to marc21"""
    translator = Translator()
    return translator.to_marc21(json_object)


def blob_to_json(blob):
    """Returns blob translated to json

    :param blob: string containg marc21 records
    :return: list of records
    """
    records = [create_record(data) for data in split_blob(blob)]
    for record in records:
        yield to_json(record)


def file_to_json(marc21_file):
    """Reads a marc21 records from file and returns them in json

    :param marc21_file: filepath to file containing marc21 records
    :return: list of json records
    """
    with open(marc21_file, 'r') as fd:
        blob = [create_record(data) for data in split_blob(fd.read())]
        return [to_json(single_record) for single_record in blob]


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
    """Checks the translation process on marc21 objects

    :param marc21_object: string of marc21 objects
    :return:
    """
    records = create_records_from_blob(marc21_object)
    json_records = to_json(records)

    result = []
    for input_record, output_record in zip(records, json_records):
        restored_input = to_marc21(output_record)

        missed_keys_number = 0
        different_keys_number = 0
        restored_keys_number = len(restored_input)

        missed_keys = []
        different_keys = []
        similar_keys = set()
        for key, value in restored_input.iteritems():
            if key not in input_record.keys():
                missed_keys_number += 1
                missed_keys.append(key)
                continue

            similar_keys.add(key)
            if restored_input[key] != input_record[key]:
                different_keys_number += 1
                different_keys.append((restored_input[key], input_record[key]))

        result.append({
            'input_keys_number': len(input_record.items()),
            'restored_keys_number': restored_keys_number,
            'missed_keys_number': missed_keys_number +
                                  len(input_record.items()) -
                                  restored_keys_number,
            'different_keys_number': different_keys_number,
            'missed_keys': missed_keys +
                           list(set(input_record.keys()) - similar_keys),
            'different_keys': different_keys,
            'correct': (missed_keys_number + different_keys_number) == 0
        })

    return result
