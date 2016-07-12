#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import common
import os
import subprocess
import unittest


class ConfigTest(common.BackpyTest):

    @classmethod
    def setUpClass(cls):
        # backup any existing config
        # set root backup dir
        super(ConfigTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(ConfigTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(ConfigTest, self).setUp()

    # try to add a folder that does not exist
    # and check nothing is added to config file
    def testAddFolderSourceNotFound(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        src = 'test'
        dest = self.dest_root
        backpy.add_directory(
            backpy.CONFIG_FILE, src, dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertEqual(size_before, size_after)

    # try to add a folder that does exist
    # check source path is added to config file
    def testAddFolderSourceFound(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'one')
        dest = os.path.join(self.dest_root, 'one')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name
    def testAddFolderWithSpaces(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to remove a folder
    def testRemoveFolder(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.delete_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name,
    # calling backpy from command line
    def testAddFolderViaCommandLine(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join(self.project_dir, 'resources', 'source_files', 'six')
        dest = os.path.join(self.dest_root, 'six')
        backpy_py = os.path.join(self.project_dir, 'backpy', 'backpy.py')
        # add part of name here to ensure spaces are passed in
        subprocess.check_output(
            [
                'python', backpy_py, '-a', '\"' + src,
                'seven\"', '\"' + dest, 'seven\"'
            ]
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))
        
    def testFail(self):
        self.assertTrue(False)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ConfigTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
