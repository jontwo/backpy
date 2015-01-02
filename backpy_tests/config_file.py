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
            backpy.init(backpy.CONFIG_FILE)
            cls.do_restore = True

        # set root backup dir
        if os.getenv("OS") == "Windows_NT":
            cls.root_dir = os.path.join(
                backpy.ROOT_PATH, 'temp', 'backpy'
            )
        else:
            cls.root_dir = os.path.join(
                backpy.ROOT_PATH, 'tmp', 'backpy'
            )
        if not os.path.exists(cls.root_dir):
            os.mkdir(cls.root_dir)

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.root_dir)
        # restore config
        if cls.do_restore:
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    def textInFile(self, filename, text):
        with open(filename) as l:
            config_contents = l.read()
            return text in config_contents

    def getFileSize(self, filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        return size

    # try to add a folder that does not exist
    # and check nothing is added to config file
    def test1AddFolderSourceNotFound(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        src = 'test'
        dest = os.path.join(self.root_dir)
        backpy.add_directory(
            backpy.CONFIG_FILE, src, dest
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertEqual(size_before, size_after)

    # try to add a folder that does exist
    # check source path is added to config file
    def test2AddFolderSourceFound(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'one')
        dest = os.path.join(self.root_dir, 'one')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join('.', src), dest
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.textInFile(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name
    def test3AddFolderWithSpaces(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.root_dir, 'six seven')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join('.', src), dest
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.textInFile(backpy.CONFIG_FILE, src))

    # try to remove a folder
    def test4RemoveFolder(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.root_dir, 'six seven')
        backpy.delete_directory(
            backpy.CONFIG_FILE, os.path.join('.', src), dest
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.textInFile(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name,
    # calling backpy from command line
    def test5AddFolderViaCommandLine(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six')
        dest = os.path.join(self.root_dir, 'six')
        backpy_py = os.path.join('.', 'backpy', 'backpy.py')
        # add part of name here to ensure spaces are passed in
        subprocess.check_output(
            ['python', backpy_py, '-a', src, 'seven', dest, 'seven']
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.textInFile(backpy.CONFIG_FILE, src))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ConfigTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
