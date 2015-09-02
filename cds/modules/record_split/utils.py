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

from collections import OrderedDict, namedtuple
from functools import partial
import json
import pprint
import traceback
import urlparse
import os
from collections import Sequence
import warnings
from six import with_metaclass
from cds.base.dojson.main import translate_json_to_marc
from dojson.contrib.marc21.utils import split_blob, create_record
from cds.base.dojson.api import translate, Translator


class SplitWarning(Warning):
    pass


class SplitException(Exception):
    pass


class Double037Field(SplitException):
    pass


class RecordSplitterMetaclass(type):
    def __new__(metacls, name, bases, dct):
        result = super(RecordSplitterMetaclass, metacls).__new__(metacls, name, bases, dct)
        result._filters = []
        result._copiers = []
        result._removers = []
        for key, value in dct.iteritems():
            if key.startswith('filter'):
                result._filters.append(partial(value, self=result))
            elif key.startswith('copy'):
                result._copiers.append(partial(value, self=result))
            elif key.startswith('remove'):
                result._removers.append(partial(value, self=result))
        return result


class RecordSplitter(with_metaclass(RecordSplitterMetaclass, object)):
    _main_type = None
    _new_type = None
    _copy_fields_list = []

    def __init__(self):
        self._next_id = 5000000

    def get_next_id(self):
        self._next_id += 1
        return self._next_id - 1  # it will be changed, it should be taken from database

    @staticmethod
    def _force_list(data):  # it is implemented in doJson, should I use function from it? or implement it here?
        if data is None:
            return []
        if not isinstance(data, (list, set)):
            return [data]
        return data

    @staticmethod
    def _reverse_force_list(data):
        if len(data) == 1:
            return data[0]
        return data

    def split_records_string(self, batch_string):
        """Splits the marcxml string to json-like structure

        If batch_string contains several records it returns
        the list of tuples (main_record, list_of_new_records)
        else it returns tuple (main_records, list_of_new_records)

        :param batch: marcxml string of records
        :return: tuple or list of tuples
        """
        assert isinstance(batch_string, basestring)
        records = [create_record(data) for data in split_blob(batch_string)]
        return self.split_records(self._reverse_force_list(records))

    def split_records(self, records):
        """Splits the container-record to separate records

        If records contains several records it returns
        the list of tuples (main_record, list_of_new_records)
        else it returns tuple (main_records, list_of_new_records)

        :param records: dict  or list containing records to split
        :return: list of lists of splitted records
        """
        assert isinstance(records, (dict, list))
        if isinstance(records, list):
            return map(self._transform_record, records)
        return self._transform_record(records)

    def _get_new_records_base(self, record):
        result = []
        # try:
        for field_filter in self._filters:
            result.extend(field_filter(record=record))
        return result
        # except Exception, e:
        #     message = "Exception filtering fields. Album: %s, exception: %s" % (record['001'][0], str(e))
        #     warnings.warn(message)
        #     raise SplitException(message)

    def _transform_record(self, record):
        assert isinstance(record, dict)

        new_records_base = self._get_new_records_base(record)
        # new_records_base = self._get_new_record_base(record)
        photo_records = [self._new_record_factory(record_base)
                         for record_base in new_records_base]

        self._set_references(record, photo_records)
        self._copy_fields(record, photo_records)
        self._set_records_types(record, photo_records)
        self._remove_fields(record)

        return record, photo_records

    def _set_records_types(self, main_records, new_records):
        """Sets main_type for the main_records and new_type for new_records"""
        set_type = lambda record, typ: record.__setitem__(u'999__', {'a': typ})

        map(partial(set_type, typ=self.__class__._main_type),
            self.__class__._force_list(main_records))
        map(partial(set_type, typ=self.__class__._new_type),
            self.__class__._force_list(new_records))

    def _new_record_factory(self, field, *args):
        key, value = field.items()[0]
        record = {
            u'001': [str(self.get_next_id())],
            key: value
        }
        return record

    def _set_references(self, main_record, new_records):
        if not main_record or not new_records:
            return
        type_tag = u'774__'
        main_recid = main_record['001'][0]

        main_type = self.__class__._main_type
        new_type = self.__class__._new_type

        assert not main_record.get(type_tag) or isinstance(main_record[type_tag], Sequence)
        main_record[type_tag] = self.__class__._force_list(main_record.get(type_tag))

        for record in new_records:
            assert not record.get(type_tag) or isinstance(record[type_tag], Sequence)
            record[type_tag] = self.__class__._force_list(record.get(type_tag))

        [rec[type_tag].append({'a': main_type, 'r': main_recid}) for rec in new_records]
        [main_record[type_tag].append({'a': new_type, 'r': rec['001'][0]}) for rec in new_records]

        main_record[type_tag] = self.__class__._reverse_force_list(main_record[type_tag])
        for record in new_records:
            record[type_tag] = self.__class__._reverse_force_list(record[type_tag])

    def _copy_fields(self, main_record, new_records):
        for field in self.__class__._copy_fields_list:
            if field in main_record:
                copy_function = getattr(self, 'copy_%s' % field,
                                        partial(self.copy_default, field=field))
                for new_record in new_records:
                    copy_function(main_record, new_record)

    def _remove_fields(self, main_record):
        for remover in self._removers:
            remover(record=main_record)

    def copy_default(self, main_record, new_record, field):
        new_record[field] = main_record[field]

    @staticmethod
    def common_filter(record, field_tag, predicate, unique_key_fun):
        # unique_key_fun = lambda media_field: urlparse.urlsplit(media_field.get('u')).path.rsplit('/', 1)[-1]
        record[field_tag] = AlbumSplitter._force_list(record[field_tag])
        new_record_base = OrderedDict()
        for field in record[field_tag]:
            if predicate(field):
                unique_key = unique_key_fun(field)
                if not new_record_base.get(unique_key):
                    new_record_base[unique_key] = []
                new_record_base[unique_key].append(field)
        return [{field_tag: l} for l in new_record_base.values()]

    @staticmethod
    def common_remove(record, field_tag, new_value):
        if new_value:
            record[field_tag] = new_value
        else:
            del record[field_tag]

class AlbumSplitter(RecordSplitter):
    _main_type = 'ALBUM'
    _new_type = 'IMAGE'
    _copy_fields_list = [
        u'037__',
        u'100__',
        u'245__',
        u'260__',
        u'269__',
        u'540__',
        u'542__',
        u'700__',
    ]

    q_allowed_hostnames = ['http://doc.cern.ch', 'http://cds.cern.ch', 'http://cdsweb.cern.ch', 'https://cds.cern.ch']
    q_banned_hostnames = ['http://preprints.cern.ch', 'http://documents.cern.ch']

    @classmethod
    def allowed_hostname(cls, url):
        check_fun = partial(lambda hostname, url: url.startswith(hostname), url=url)
        return any(map(check_fun, cls.q_allowed_hostnames))
        # return urlparse.urlsplit(url).hostname.lower() in cls.q_allowed_hostnames

    @classmethod
    def banned_hostname(cls, url):
        check_fun = partial(lambda hostname, url: url.startswith(hostname), url=url)
        return any(map(check_fun, cls.q_banned_hostnames))
        # return urlparse.urlsplit(url).hostname.lower() in cls.q_banned_hostnames


    @classmethod
    def predicate(cls, field):
        return (
            (
                not field.get('x')
                or
                not field.get('x').startswith('icon')
            )
            and
            (
                field.get('u')
                or
                (
                    field.get('q')
                    and
                    cls.allowed_hostname(field.get('q'))
                )
            )
        )

    def filter_8564_(self, record):
        unique_key_fun = lambda media_field: urlparse.urlsplit(media_field.get('u') or media_field.get('q')).path.rsplit('/', 1)[-1]
        return RecordSplitter.common_filter(record, u'8564_', self.predicate, unique_key_fun)

    def filter_8567_(self, record):
        unique_key_fun = lambda media_field: media_field.get('8')
        predicate_fun = lambda field: field.get('2') == 'MediaArchive'
        return RecordSplitter.common_filter(record, u'8567_', predicate_fun, unique_key_fun)

    def remove_8564_(self, record):
        field_tag = u'8564_'
        is_known_hostname_fun = partial(lambda x, known:
                                        len([False for y in known if x.startswith(y)]) != 0, known=self.q_allowed_hostnames+self.q_banned_hostnames)

        if record.get(field_tag):
            q_list = [is_known_hostname_fun(elm.get('q')) for elm in record[u'8564_'] if elm.get('q')]
            if q_list:
                assert all(q_list), record[field_tag]  # all hostnames are aknowledged

        cleared_field = []
        for field in AlbumSplitter._force_list(record[field_tag]):
            if field.get('x'):
                if field['x'].startswith('icon'):
                    continue
            if not self.predicate(field):
                record_url = field.get('q')
                if not record_url or not (
                        AlbumSplitter.allowed_hostname(record_url) or
                        AlbumSplitter.banned_hostname(record_url)
                ):
                    assert False, "Uncovered case in album %s for field 8564_: %s" % (record['001'][0], str(field))
                    # cleared_field.append(field)

        RecordSplitter.common_remove(record, field_tag, cleared_field)

    def remove_8567_(self, record):
        field_tag = u'8567_'
        cleared_field = [field for field in AlbumSplitter._force_list(record[field_tag]) if field.get('2') != 'MediaArchive']
        RecordSplitter.common_remove(record, field_tag, cleared_field)

    def copy_037__(self, main_record, new_record):
        if not isinstance(main_record[u'037__'], dict):
            raise Double037Field
        common_field = main_record[u'037__']['a']
        counter = None

        if new_record.get(u'8564_'):
            counter = new_record.get(u'8564_')[0].get('c', '')
        elif new_record.get(u'8567_'):
            counter = new_record.get(u'8567_')[0].get('8', '01')

        if not counter:
            warnings.warn("Counter isn't specified")

        new_record[u'037__'] = {
            'a': '-'.join(filter(lambda x: x, [common_field, counter]))
        }

    def _transform_record(self, record):
        record, photo_records = super(AlbumSplitter, self)._transform_record(record)
        for photo in photo_records:
            if photo.get(u'8564_'):
                photo[u'8564_'] = self._reverse_force_list(photo[u'8564_'])
            if photo.get(u'8567_'):
                photo[u'8567_'] = self._reverse_force_list(photo[u'8567_'])

        return record, photo_records













def test():
    # filepath = '/home/theer/Documents/CERN/split2.xml'
    filepath = '/home/theer/Documents/CERN/split-one-8564.xml'
    # filepath = '/home/theer/Documents/CERN/.xml'
    with open(filepath, 'r') as fd:
        a = AlbumSplitter()
        return a.split_records_string(fd.read())


def test_batch():
    filepath = '/home/theer/Documents/CERN/photos_to_split.xml'
    # filepath = '/home/theer/Documents/CERN/split/tiny-photos-to-split.xml'
    with open(filepath, 'r') as fd:
        splitter = AlbumSplitter()
        records = [create_record(data) for data in split_blob(fd.read())]
        counter = 0
        result_path = '/home/theer/Documents/CERN/split/test_out'
        for album in records:
            try:
                album, photos = splitter.split_records(album)
                path = os.path.join(result_path, album['001'][0])
                os.mkdir(path)
                with open(os.path.join(path, 'album'), 'w') as fd:
                    fd.write(pprint.pformat(album, indent=4))
                for photo in photos:
                    with open(os.path.join(path, photo['001'][0]), 'w') as fd:
                        fd.write(pprint.pformat(photo, indent=4))

                counter += 1
                if counter % 1000 == 0:
                    print '%s/%s' % (counter, len(records))
            except Double037Field, e:
                print '=============== Double 037 field: %s' % album['001'][0]
            except SplitException, e:
                print ('='*15 + 'Album: %s' + '='*15) % album['001'][0]
                pprint.pprint(e.args)
                print '=' * 35
            except Exception, e:
                print ('!'*15 + 'Album: %s' + '!'*15) % album['001'][0]
                traceback.print_exc()
                pprint.pprint(e.args)
                print '!' * 35


def test_integration_batch():
    # filepath = '/home/theer/Documents/CERN/photos_to_split.xml'
    # filepath = '/home/theer/Documents/CERN/split/tiny-photos-to-split.xml'
    filepath = '/home/theer/Documents/CERN/photos_to_split.xml'
    ok_results = []
    errors = []
    exceptions = []
    with open(filepath, 'r') as fd:
        records = [create_record(data) for data in split_blob(fd.read())]
        for album in records:
            try:
                album_result, photo_results = test_integration(album)
                translation_results = [album_result] + photo_results
                for result in translation_results:
                    if not result['correct']:
                        print 'Error for album: %s' % album['001'][0]
                        errors.append(result)
                    else:
                        ok_results.append(result)

            except Exception:
                print 'Exception for album: %s' % album['001'][0]
                traceback.print_exc()
                exceptions.append(traceback.format_exc())

    print 'OK albums: %s' % len(ok_results)
    print 'Error albums: %s' % len(errors)
    print 'Critical albums: %s' % len(exceptions)
    return ok_results, errors, exceptions

def test_integration_file(filepath=None):
    if not filepath:
        filepath = '/home/theer/Documents/CERN/split-one-8564.xml'
    with open(filepath, 'r') as fd:
        return test_integration(fd.read())

def test_integration(input_string):
    # filepath = '/home/theer/Documents/CERN/.xml'
    a = AlbumSplitter()
    if isinstance(input_string, basestring):
        album, photos = a.split_records_string(input_string)
    else:
        album, photos = a.split_records(input_string)

    translated_album = translate(album)
    translated_photos = map(translate, photos)

    album_result = test_translation(album, translated_album, True)
    photo_results = map(lambda (x, y): test_translation(x, y), zip(photos, translated_photos))

    return album_result, photo_results
    # return translated_album, translated_photos


def test_translation(xml_input, json_output, album=False):
    json_string = json.dumps(json_output)

    reverted_translation = translate_json_to_marc(json_string, album)[0]
    result = Translator.test_correctness(xml_input, json_output)

    return result
    # missed_keys_number = 0
    # different_keys_number = 0
    # reverted_keys_number = len(reverted_translation)
    #
    # missed_keys = []
    # different_keys = []
    # similar_keys = set()
    # for key, value in reverted_translation.iteritems():
    #     key_with_ind = key
    #     if isinstance(value, dict) and (value.get('$ind1') or value.get('$ind2')):
    #         key_with_ind = key + value.pop('$ind1', '_') + value.pop('$ind2', '_')
    #     if key_with_ind not in xml_input.keys():
    #         missed_keys_number += 1
    #         missed_keys.append(key_with_ind)
    #         import pdb
    #         pdb.set_trace()
    #         continue
    #
    #     similar_keys.add(key)
    #     if reverted_translation[key] != xml_input[key_with_ind]:
    #         different_keys_number += 1
    #         different_keys.append((reverted_translation[key], xml_input[key_with_ind]))
    # print "="*20, "Album:", album, "Id:", xml_input['001'], "="*20
    # print "Original number of entries: {0}".format(len(xml_input.items()))
    # print "Reverted number of entries: {0}".format(reverted_keys_number)
    # print "Missed keys: {0}".format(missed_keys_number + len(xml_input.items()) - reverted_keys_number)
    # print "Different keys: {0}".format(different_keys_number)
    # print "="*40
    # print "Missed keys: " + str(missed_keys + list(set(xml_input.keys()) - similar_keys))
    # print "Different keys:\n" + '\n'.join([str(key_pair) for key_pair in different_keys])
    # print "="*40
    #
    # import pdb
    # pdb.set_trace()
