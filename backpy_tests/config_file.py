#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import os
import subprocess
import unittest
from shutil import copy2


class ConfigTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.backpy.orig')
    root_dir = '.'
    do_restore = False

    @classmethod
    def setUpClass(cls):
        # backup any existing config
        if os.path.exists(backpy.CONFIG_FILE):
            if os.path.exists(cls.config_backup):
                # delete old backup
                os.unlink(cls.config_backup)
            os.rename(backpy.CONFIG_FILE, cls.config_backup)
            backpy.set_up_logging(0)
            cls.do_restore = True

        # set root backup dir
        if os.getenv("OS") == "Windows_NT":
            cls.dest_root = os.path.join(
                backpy.ROOT_PATH, 'temp', 'backpy'
            )
        else:
            cls.dest_root = os.path.join(
                backpy.ROOT_PATH, 'tmp', 'backpy'
            )
        if not os.path.exists(cls.dest_root):
            os.mkdir(cls.dest_root)

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.do_restore:
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    def setUp(self):
        # start test with blank config
        if os.path.exists(backpy.CONFIG_FILE):
            os.unlink(backpy.CONFIG_FILE)
        backpy.init(backpy.CONFIG_FILE)

    def add_one_folder(self):
        src = os.path.join(self.root_dir, 'resources', 'source_files', 'one')
        dest = os.path.join(self.dest_root, 'one')
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def add_six_seven_folder(self):
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.root_dir, src), dest
        )

    def text_in_file(self, filename, text):
        with open(filename) as l:
            config_contents = l.read()
            return text in config_contents

    def get_file_size(self, filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        return size

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
            backpy.CONFIG_FILE, os.path.join(self.root_dir, src), dest
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
            backpy.CONFIG_FILE, os.path.join(self.root_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to remove a folder
    def testRemoveFolder(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder()

        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.delete_directory(
            backpy.CONFIG_FILE, os.path.join(self.root_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name,
    # calling backpy from command line
    def testAddFolderViaCommandLine(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six')
        dest = os.path.join(self.dest_root, 'six')
        backpy_py = os.path.join(self.root_dir, 'backpy', 'backpy.py')
        # add part of name here to ensure spaces are passed in
        subprocess.check_output(
            ['python', backpy_py, '-a', src, 'seven', dest, 'seven']
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ConfigTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
