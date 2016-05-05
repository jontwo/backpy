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
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 1)

    # 2. do 1, change a file, backup again
    def testSecondBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change a file
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('some more text\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 1)

    # 3. do 2, change a file, backup again
    def testThirdBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change a file
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('some more text\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change a file
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('yet more text\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 3)
        self.assertEqual(zips_in_six_seven, 1)

    # 4. do 3, delete the file, backup again
    def testDeleteFileAndBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change a file
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('some more text\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change a file
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('yet more text\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete file
        os.unlink(os.path.join(self.src_root, 'one', 'four', 'five'))

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 4)
        self.assertEqual(zips_in_six_seven, 1)

    # 5. do 1, add a new file, backup again
    def testAddNewFileAndBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # create new file
        with open(os.path.join(self.src_root, 'six seven', 'eleven'), 'a') as f:
            f.write('new file\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 6. do 1, add a folder, backup again
    def testAddNewFolderAndBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # create a new folder and file
        os.mkdir(os.path.join(self.src_root, 'six seven', 'twelve'))
        with open(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'a') as f:
            f.write('new file\n')

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 7. do 6, delete a different folder, backup again
    def testDeleteFolderAndBackup(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # create a new folder and file
        os.mkdir(os.path.join(self.src_root, 'six seven', 'twelve'))
        with open(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'a') as f:
            f.write('new file\n')

        # delete a folder
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'four'))

        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 2)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(BackupTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
