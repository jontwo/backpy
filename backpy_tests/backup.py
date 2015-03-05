#!/usr/bin/python2
# -*- coding: utf-8 -*-

import backpy
import common
import os
import unittest

class BackupTest(common.BackpyTest):

    @classmethod
    def setUpClass(cls):
        # backup any existing config
        # set root backup dir
        super(BackupTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(BackupTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(BackupTest, self).setUp()
        # clear dest folder
        backpy.delete_temp_files(self.dest_root)
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder()
        self.one_folder = os.path.join(self.dest_root, 'one')
        self.six_seven_folder = os.path.join(self.dest_root, 'six seven')

    # perform backup into an empty destination folder
    def testInitialBackup(self):
        # make sure dest is empty
        zips_in_one = self.count_files(
            os.path.join(self.one_folder, '*.tar.gz')
        )
        zips_in_six_seven = self.count_files(
            os.path.join(self.six_seven_folder, '*.tar.gz')
        )
        self.assertEqual(zips_in_one + zips_in_six_seven, 0)

        # do backup
        backup_dirs = backpy.read_directory_list(backpy.CONFIG_FILE)
        for directory in backup_dirs:
            backpy.perform_backup(directory)

        # count zips again
        zips_in_one = self.count_files(
            os.path.join(self.one_folder, '*.tar.gz')
        )
        zips_in_six_seven = self.count_files(
            os.path.join(self.six_seven_folder, '*.tar.gz')
        )
        self.assertEqual(zips_in_one + zips_in_six_seven, 2)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(BackupTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
