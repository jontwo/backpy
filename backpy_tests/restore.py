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
        super(RestoreTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(RestoreTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(RestoreTest, self).setUp()
        # clear dest folder
        backpy.delete_temp_files(self.dest_root)
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder()
        self.one_folder = os.path.join(self.dest_root, 'one')
        self.six_seven_folder = os.path.join(self.dest_root, 'six seven')

    # 1. do backup 1, delete 1 file, restore the file by full path
    def testRestoreOneFileFullPath(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete file
        os.unlink(os.path.join(self.src_root, 'one', 'four', 'five'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), [os.path.join(self.src_root, 'one', 'four', 'five')], 0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 2. do backup 1, delete 1 file, restore the file by name only
    def testRestoreOneFileByName(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete file
        os.unlink(os.path.join(self.src_root, 'one', 'four', 'five'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), ['five'], 0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 3. do backup 1, delete file, full restore
    def testFullRestoreOneFileDeleted(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete file
        os.unlink(os.path.join(self.src_root, 'one', 'four', 'five'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), chosen_index=0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 4. do backup 1, delete folder, restore the folder by full path
    def testRestoreOneFolderByFullPath(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete a folder
        backpy.delete_temp_files(os.path.join(self.src_root, 'six seven'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), [os.path.join(self.src_root, 'six seven')])

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 5. do backup 1, delete folder, restore the folder by name only
    def testRestoreOneFolderByName(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete a folder
        backpy.delete_temp_files(os.path.join(self.src_root, 'six seven'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), ['six seven'])

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 6. do backup 1, delete folder, full restore
    def testFullRestoreOneFolderDeleted(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # delete a folder
        backpy.delete_temp_files(os.path.join(self.src_root, 'six seven'))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), chosen_index=0)

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 7. do backup 1, restore a file, should be skipped as file is not changed
    def testRestoreOneFileUnchanged(self):
        # do backup
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

        # change file timestamp wihout changing contents
        filename = os.path.join(self.src_root, 'one', 'nine ten')
        with open(filename, 'r') as f:
            file_content = f.read()
        with open(filename, 'w') as f:
            f.write(file_content)
        modified_time_before = os.path.getmtime(filename)

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), ['nine ten'], 0)

        # check modified time has not changed back
        modified_time_after = os.path.getmtime(filename)
        self.assertEqual(modified_time_before, modified_time_after)

    # 8. do backup 3, delete everything, full restore
    def testDeleteEverythingAndFullRestore(self):
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

        # delete all folders
        backpy.delete_temp_files(self.src_root)

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), chosen_index=0)

        # check folders are there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('one', files_in_src)
        self.assertIn('six seven', files_in_src)

        # check correct version of changed file is restored
        self.assertEqual('yet more text', self.get_last_line(os.path.join(self.src_root, 'one', 'four', 'five')))

    # 9. do backup 4, restore the original version of the file
    def testDeleteFileAndRestoreOriginal(self):
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

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), ['five'], chosen_index=2)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

        # check correct version of changed file is restored
        self.assertEqual('some text', self.get_last_line(os.path.join(self.src_root, 'one', 'four', 'five')))

    # 10. do backup 7, full restore, folder should still be deleted
    def testDeleteFolderAndFullRestore(self):
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

        # delete all folders
        backpy.delete_temp_files(os.path.join(self.src_root))

        # do restore
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), chosen_index=0)

        # check removed folder is not there
        files_in_src = os.listdir(os.path.join(self.src_root, 'one'))
        self.assertNotIn('four', files_in_src)

        # check new file is restored
        self.assertEqual('new file', self.get_last_line(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven')))

    # 11. TODO do backup and restore using UNC paths
    # should probably try this but not sure how, as user will have to set up a share prior to running test

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(RestoreTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
