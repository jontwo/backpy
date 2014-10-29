#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import os
import unittest


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
            ConfigTest.root_dir = os.path.join(
                backpy.ROOT_PATH, 'temp', 'backpy'
            )
        else:
            ConfigTest.root_dir = os.path.join(
                backpy.ROOT_PATH, 'tmp', 'backpy'
            )

    @classmethod
    def tearDownClass(cls):
        # restore config
        if cls.do_restore:
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    def getFileSize(self, filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.exists(filename)
        return size

    # try to add a folder that does not exist
    # and check nothing is added to config file
    def testAddFolderSourceNotFound(self):
        size_before = self.getFileSize(backpy.CONFIG_FILE)
        backpy.add_directory(
            backpy.CONFIG_FILE,
            'test',
            os.path.join(ConfigTest.root_dir)
        )

        size_after = self.getFileSize(backpy.CONFIG_FILE)
        self.assertEqual(size_before, size_after)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ConfigTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
