#!/usr/bin/python2
# -*- coding: utf-8 -*-

# StdLib Imports
import os
import unittest

# Project Imports
import backpy
import common
from backpy.helpers import get_file_hash


class IndexTest(common.BackpyTest):
    index = None

    @classmethod
    def setUpClass(cls):
        super(IndexTest, cls).setUpClass()

        # create index
        cls.index = backpy.FileIndex(cls.src_root)
        cls.index.gen_index()

        # index file from backpy v1.4.7
        cls.index_147 = os.path.join(backpy.TEMP_DIR, 'resources', 'index_147')

        # index file from backpy v1.5.0
        cls.index_150 = os.path.join(backpy.TEMP_DIR, 'resources', 'index_150')

    def list_all_files(self):
        return [
            os.path.join(self.src_root, 'three'),
            os.path.join(self.src_root, 'one/nine ten'),
            os.path.join(self.src_root, 'one/four/five'),
            os.path.join(self.src_root, 'six seven/eight')
        ]

    def list_all_dirs(self):
        return [
            self.src_root,
            os.path.join(self.src_root, 'one'),
            os.path.join(self.src_root, 'one/four'),
            os.path.join(self.src_root, 'six seven')
        ]

    def testListFiles(self):
        expected_files = self.list_all_files()

        actual_files = self.index.files()

        self.assertItemsEqual(expected_files, actual_files)

    def testListDirs(self):
        expected_dirs = self.list_all_dirs()

        actual_dirs = self.index.dirs()

        self.assertItemsEqual(expected_dirs, actual_dirs)

    def testSkips(self):
        # create fresh index with exclusions
        expected_rules = ['a', 'b', 'c']
        index = backpy.FileIndex(self.src_root, exclusion_rules=expected_rules)

        actual_rules = index.skips()

        self.assertItemsEqual(expected_rules, actual_rules)

    def testGlobalSkips(self):
        # create fresh index with exclusions
        initial_rules = ['a', 'b', 'c']
        added_rules = ['d,e']
        expected_rules = ['a', 'b', 'c', 'd', 'e']
        backpy.add_global_skip(backpy.CONFIG_FILE, added_rules)
        index = backpy.FileIndex(self.src_root, exclusion_rules=initial_rules)

        actual_rules = index.skips()

        self.assertItemsEqual(expected_rules, actual_rules)

    def testIsValidBadFile(self):
        self.assertFalse(self.index.is_valid('bad file'))

    def testIsValidNoRules(self):
        self.assertTrue(self.index.is_valid(self.get_one_four_five_path()))

    def testIsValidSkippedFile(self):
        # create fresh index with one exclusion
        expected_rules = ['*four*']
        index = backpy.FileIndex(self.src_root, exclusion_rules=expected_rules)

        self.assertFalse(index.is_valid(self.get_one_four_five_path()))

    def testHashExactPath(self):
        expected_hash = get_file_hash(self.get_one_four_five_path())

        actual_hash = self.index.hash(self.get_one_four_five_path())

        self.assertEqual(expected_hash, actual_hash)

    def testHashExactPathNotFound(self):
        actual_hash = self.index.hash('bad file')

        self.assertIsNone(actual_hash)

    def testHashNameOnly(self):
        expected_hash = get_file_hash(self.get_one_four_five_path())

        actual_hash = self.index.hash('five', exact_match=False)

        self.assertEqual(expected_hash, actual_hash)

    def testHashNameOnlyNotFound(self):
        actual_hash = self.index.hash('bad file', exact_match=False)

        self.assertIsNone(actual_hash)

    def testIsFolderExactPath(self):
        self.assertTrue(self.index.is_folder(self.src_root))

    def testIsFolderExactPathNotFound(self):
        self.assertFalse(self.index.is_folder('bad folder'))

    def testIsFolderNameOnly(self):
        self.assertTrue(self.index.is_folder('source_files', exact_match=False))

    def testIsFolderNameOnlyNotFound(self):
        self.assertFalse(self.index.is_folder('bad folder', exact_match=False))

    def testGetDiffNoIndex(self):
        expected_diff = self.list_all_files()

        actual_diff = self.index.get_diff()

        self.assertItemsEqual(expected_diff, actual_diff)

    def testGetDiffNoChange(self):
        expected_diff = []

        actual_diff = self.index.get_diff(self.index)

        self.assertEqual(expected_diff, actual_diff)

    def testGetDiffChangedFile(self):
        expected_diff = [self.get_one_four_five_path()]
        # change a file and regenerate index
        self.change_one_four_five('some text')
        new_index = backpy.FileIndex(self.src_root)
        new_index.gen_index()

        actual_diff = self.index.get_diff(new_index)

        self.assertEqual(expected_diff, actual_diff)

    def testGetDiffDeletedFile(self):
        expected_diff = [self.get_one_four_five_path()]
        # delete a file and regenerate index
        self.delete_one_four_five()
        new_index = backpy.FileIndex(self.src_root)
        new_index.gen_index()

        actual_diff = self.index.get_diff(new_index)

        self.assertEqual(expected_diff, actual_diff)

    def testGetMissingNoIndex(self):
        expected_missing = []

        actual_missing = self.index.get_missing()

        self.assertEqual(expected_missing, actual_missing)

    def testGetMissingNoChange(self):
        expected_missing = []

        actual_missing = self.index.get_missing(self.index)

        self.assertEqual(expected_missing, actual_missing)

    def testGetMissingDeletedFile(self):
        expected_missing = [self.get_one_four_five_path()]
        # delete a file and regenerate index
        self.delete_one_four_five()
        new_index = backpy.FileIndex(self.src_root)
        new_index.gen_index()

        actual_missing = new_index.get_missing(self.index)

        self.assertEqual(expected_missing, actual_missing)

    def testWriteIndex(self):
        expected_text = self.file_contents(self.index_147)
        tmp_path = os.path.join(backpy.TEMP_DIR, '.{}_index'.format(self.timestamp))

        self.index.write_index(tmp_path)
        actual_text = self.file_contents(tmp_path)

        self.assertItemsEqual(expected_text, actual_text)

    # Note: this test currently fails, as src_root is added twice to the index
    # need to update read_index to check for duplicate entries
    def testReadIndex(self):
        # create a new index and read existing (old style) index file
        index = backpy.FileIndex(self.src_root)
        index.read_index(self.index_147)

        # check files and dirs
        expected_files = self.list_all_files()
        actual_files = index.files()
        self.assertItemsEqual(expected_files, actual_files)

        expected_dirs = self.list_all_dirs()
        actual_dirs = index.dirs()
        self.assertItemsEqual(expected_dirs, actual_dirs)

    def testReadIndexNotFound(self):
        # create a new index and try to read non-existant index file
        index = backpy.FileIndex(self.src_root)
        index.read_index()

        # check files and dirs
        expected_files = []
        actual_files = index.files()
        self.assertItemsEqual(expected_files, actual_files)

        # source is always added
        expected_dirs = [self.src_root]
        actual_dirs = index.dirs()
        self.assertItemsEqual(expected_dirs, actual_dirs)

    def testReadIndex150(self):
        # create a new index and read existing (new style) index file
        # headings should be ignored, except files and dirs
        index = backpy.FileIndex(self.src_root)
        index.read_index(self.index_150)

        # check files and dirs
        expected_files = self.list_all_files()
        actual_files = index.files()
        self.assertItemsEqual(expected_files, actual_files)

    def testReadIndexCheckAdb(self):
        # create a new index and read existing (new style) index file
        index = backpy.FileIndex(self.src_root)
        index.read_index(self.index_150)

        self.assertFalse(index.__adb__)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(IndexTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
