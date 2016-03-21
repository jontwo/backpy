#!/usr/bin/python2
# -*- coding: utf-8 -*-

import backpy
import common
import os
import unittest


class RestoreTest(common.BackpyTest):

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

    # first restore test
    def testBlah(self):
        pass

    # 1. do Backup 1, restore 1 file, check it is found
    # 2. do Backup 1, delete file, full restore
    # 3. do Backup 1, delete folder, full restore
    # 4. do Backup 4, restore file, check correct version found
    # 5. do Backup 7, full restore, folder should still be deleted

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(BackupTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
