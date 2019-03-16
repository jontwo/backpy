# -*- coding: utf-8 -*-

# StdLib Imports
import os
import unittest

# Project Imports
import backpy
from . import common


class HelpersTest(common.BackpyTest):
    @classmethod
    def setUpClass(cls):
        super(HelpersTest, cls).setUpClass()
        cls.test_config_dict = {
            'default': [],
            'k1': ['some text'],
            'k2': ['more text']
        }
        cls.test_config_string = '[default]\n[k1]\nsome text\n[k2]\nmore text\n'
        cls.config_path = os.path.join(backpy.TEMP_DIR, 'test_config')

    def tearDown(cls):
        if os.path.exists(cls.config_path):
            os.remove(cls.config_path)

    def testStringEquals(self):
        string_1 = 'some text'
        string_2 = 'some text'

        self.assertTrue(backpy.helpers.string_equals(string_1, string_2))

    def testStringDoesNotEqual(self):
        string_1 = 'some text'
        string_2 = 'some other text'

        self.assertFalse(backpy.helpers.string_equals(string_1, string_2))

    def testStringContains(self):
        string_1 = 'some'
        string_2 = 'some text'

        self.assertTrue(backpy.helpers.string_contains(string_1, string_2))

    def testStringDoesNotContain(self):
        string_1 = 'other'
        string_2 = 'some text'

        self.assertFalse(backpy.helpers.string_contains(string_1, string_2))

    def testStringStartsWith(self):
        string_1 = 'some'
        string_2 = 'some text'

        self.assertTrue(backpy.helpers.string_startswith(string_1, string_2))

    def testStringDoesNotStartWith(self):
        string_1 = 'text'
        string_2 = 'some text'

        self.assertFalse(backpy.helpers.string_startswith(string_1, string_2))

    def testListContains(self):
        string_1 = 'a'
        list_2 = ['a', 'b', 'c']

        self.assertTrue(backpy.helpers.list_contains(string_1, list_2))

    def testListDoesNotContain(self):
        string_1 = 'd'
        list_2 = ['a', 'b', 'c']

        self.assertFalse(backpy.helpers.list_contains(string_1, list_2))

    def testGetFilenameIndex(self):
        string_1 = 'b'
        list_2 = [
            os.path.join('path', 'to', 'a'),
            os.path.join('path', 'to', 'b'),
            os.path.join('path', 'to', 'c')
        ]
        expected_index = 1

        actual_index = backpy.helpers.get_filename_index(string_1, list_2)
        self.assertEqual(expected_index, actual_index)

    def testGetFilenameIndexIsNone(self):
        string_1 = 'd'
        list_2 = [
            os.path.join('path', 'to', 'a'),
            os.path.join('path', 'to', 'b'),
            os.path.join('path', 'to', 'c')
        ]

        self.assertIsNone(backpy.helpers.get_filename_index(string_1, list_2))

    def testGetFolderIndex(self):
        string_1 = 'd'
        list_2 = [
            os.path.join('a', 'b', 'c'),
            os.path.join('d', 'e'),
            os.path.join('f')
        ]
        expected_index = 1

        actual_index = backpy.helpers.get_folder_index(string_1, list_2)
        self.assertEqual(expected_index, actual_index)

    def testGetFolderIndexIsNone(self):
        string_1 = 'd'
        list_2 = [
            os.path.join('path', 'to', 'a'),
            os.path.join('path', 'to', 'b'),
            os.path.join('path', 'to', 'c')
        ]

        self.assertIsNone(backpy.helpers.get_folder_index(string_1, list_2))

    def testHandleArgSpaces(self):
        src = os.path.join(self.project_dir, 'resources', 'source_files', 'six')
        dest = os.path.join(self.dest_root, 'six')
        args = ['backpy', '-a', '\"' + src, 'seven\"', '\"' + dest, 'seven\"']
        expected = ['backpy', '-a', '{} seven'.format(src), '{} seven'.format(dest)]

        actual = backpy.helpers.handle_arg_spaces(args)

        self.assertEqual(expected, actual)

    def testHandleArgSpacesMismatchedQuotes(self):
        expected = ['some', '\"string', 'with\"', 'mismatched\"', 'quotes']

        # should come back unchanged
        actual = backpy.helpers.handle_arg_spaces(expected)

        self.assertEqual(expected, actual)

    def testGetFileHashFilename(self):
        filename = os.path.join(self.src_root, 'three')
        expected_hash = '4d93d51945b88325c213640ef59fc50b'

        actual_hash = backpy.helpers.get_file_hash(filename)

        self.assertEqual(expected_hash, actual_hash)

    def testGetFileHashSize(self):
        filename = 'some file'
        filesize = 100
        expected_hash = 'dee6421b215a8579c17d1704c964e1e8'

        actual_hash = backpy.helpers.get_file_hash(filename, size=filesize)

        self.assertEqual(expected_hash, actual_hash)

    def testGetFileHashBadPath(self):
        filename = 'some file'

        self.assertIsNone(backpy.helpers.get_file_hash(filename))

    def testGetConfigVersion(self):
        expected_version = self.get_backpy_version()

        actual_version = backpy.helpers.get_config_version(backpy.CONFIG_FILE)

        self.assertEqual(expected_version, actual_version)

    def testGetConfigBadVersion(self):
        # overwrite config with some text
        with open(backpy.CONFIG_FILE, 'w+') as f:
            f.write('some text\n')

        expected_version = 0

        actual_version = backpy.helpers.get_config_version(backpy.CONFIG_FILE)

        self.assertEqual(expected_version, actual_version)

    def testGetGlobalSkips(self):
        expected_skips = ['*.jpg,*.tif']

        self.add_global_skips(expected_skips)

        actual_skips = backpy.helpers.get_config_key(backpy.CONFIG_FILE, backpy.helpers.SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def testGetConfigKeyNotFound(self):
        expected_value = []

        actual_value = backpy.helpers.get_config_key(backpy.CONFIG_FILE, 'not found')

        self.assertCountEqual(expected_value, actual_value)

    def testGetConfigKeyBadPath(self):
        expected_value = []

        actual_value = backpy.helpers.get_config_key('some file', 'not found')

        self.assertCountEqual(expected_value, actual_value)

    def testReadConfigFile(self):
        expected_values = self.test_config_dict
        with open(self.config_path, 'w+') as f:
            f.write(self.test_config_string)

        actual_values = backpy.helpers.read_config_file(self.config_path)

        self.assertCountEqual(expected_values, actual_values)

    def testReadConfigFileBadPath(self):
        expected_values = {'default': []}

        actual_values = backpy.helpers.read_config_file('')

        self.assertCountEqual(expected_values, actual_values)

    def testWriteConfigFile(self):
        # turn strings into lists so order is not important
        expected_contents = self.test_config_string.split('\n')

        backpy.helpers.write_config_file(self.config_path, self.test_config_dict)
        with open(self.config_path) as f:
            actual_contents = f.read().split('\n')

        self.assertCountEqual(expected_contents, actual_contents)

    def testWriteConfigFileBadPath(self):
        try:
            backpy.helpers.write_config_file('', self.test_config_dict)
        except IOError:
            self.fail('write_config_file raised an IOError!')

    def testUpdateConfigFile(self):
        with open(self.config_path, 'w+') as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.replace('more', 'updated').split('\n')

        backpy.helpers.update_config_file(self.config_path, 'k2', 'updated text')
        with open(self.config_path) as f:
            actual_contents = f.read().split('\n')

        self.assertCountEqual(expected_contents, actual_contents)

    def testUpdateConfigFileNewKey(self):
        with open(self.config_path, 'w+') as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.split('\n')
        expected_contents.append('[k3]')
        expected_contents.append('new text')

        backpy.helpers.update_config_file(self.config_path, 'k3', 'new text')
        with open(self.config_path) as f:
            actual_contents = f.read().split('\n')

        self.assertCountEqual(expected_contents, actual_contents)

    def testUpdateConfigFileAppendKey(self):
        with open(self.config_path, 'w+') as f:
            f.write(self.test_config_string)
        expected_contents = '{}extra text\n'.format(self.test_config_string).split('\n')

        backpy.helpers.update_config_file(self.config_path, 'k2', 'extra text', overwrite=False)
        with open(self.config_path) as f:
            actual_contents = f.read().split('\n')

        self.assertCountEqual(expected_contents, actual_contents)

    def testUpdateConfigFileAppendKeySameValue(self):
        with open(self.config_path, 'w+') as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.split('\n')

        backpy.helpers.update_config_file(self.config_path, 'k1', 'some text', overwrite=False)
        with open(self.config_path) as f:
            actual_contents = f.read().split('\n')

        self.assertCountEqual(expected_contents, actual_contents)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(HelpersTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
