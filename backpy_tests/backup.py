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

    # 1. perform backup into an empty destination folder
    def testInitialBackup(self):
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 1)

    # 2. do 1, change a file, backup again
    def testSecondBackup(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 1)

    # 3. do 2, change a file, backup again
    def testThirdBackup(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 3)
        self.assertEqual(zips_in_six_seven, 1)

    # 4. do 3, delete the file, backup again
    def testDeleteFileAndBackup(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()

        # delete file
        self.delete_one_four_five()

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 4)
        self.assertEqual(zips_in_six_seven, 1)

    # 5. do 1, add a new file, backup again
    def testAddNewFileAndBackup(self):
        self.do_backup()

        self.create_file(os.path.join(self.src_root, 'six seven', 'eleven'), 'new file\n')

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 6. do 1, add a folder, backup again
    def testAddNewFolderAndBackup(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, 'six seven', 'twelve'))
        self.create_file(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'new file\n')

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 7. do 6, delete a different folder, backup again
    def testDeleteFolderAndBackup(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, 'six seven', 'twelve'))
        self.create_file(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'new file\n')

        # delete a folder
        self.delete_one_four()

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 2)

    # 8. do 1 (with a skip), change a file in skipped folder, backup again
    def testAddSkipAndBackup(self):
        # add skip
        skips = []
        skips.append(os.path.join(self.src_root, 'one'))
        skips.append(os.path.join(self.dest_root, 'one'))
        skips.append(os.path.join(self.src_root, 'one', 'four'))
        backpy.add_skip(backpy.CONFIG_FILE, skips)

        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 1)

    # 9. do 1 (with a wildcard skip), change a file in skipped folder, backup again
    def testAddSkipWithWildcard(self):
        # add skip
        skips = []
        skips.append(os.path.join(self.src_root, 'six seven'))
        skips.append(os.path.join(self.dest_root, 'six seven'))
        skips.append('seven')
        backpy.add_skip(backpy.CONFIG_FILE, skips, True)

        self.do_backup()

        self.create_file(os.path.join(self.src_root, 'six seven', 'eight'), 'some more text\n')

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 0)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(BackupTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
