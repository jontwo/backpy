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
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore([os.path.join(self.src_root, 'one', 'four', 'five')], 0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 2. do backup 1, delete 1 file, restore the file by name only
    def testRestoreOneFileByName(self):
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore(['five'], 0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 3. do backup 1, delete file, full restore
    def testFullRestoreOneFileDeleted(self):
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore(chosen_index=0)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

    # 4. do backup 1, delete folder, restore the folder by full path
    def testRestoreOneFolderByFullPath(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore([os.path.join(self.src_root, 'six seven')])

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 5. do backup 1, delete folder, restore the folder by name only
    def testRestoreOneFolderByName(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore(['six seven'])

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 6. do backup 1, delete folder, full restore
    def testFullRestoreOneFolderDeleted(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore(chosen_index=0)

        # check folder is there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('six seven', files_in_src)

    # 7. do backup 1, restore a file, should be skipped as file is not changed
    def testRestoreOneFileUnchanged(self):
        self.do_backup()

        # change file timestamp wihout changing contents
        filename = os.path.join(self.src_root, 'one', 'nine ten')
        with open(filename, 'r') as f:
            file_content = f.read()
        with open(filename, 'w') as f:
            f.write(file_content)
        modified_time_before = os.path.getmtime(filename)

        self.do_restore(['nine ten'], 0)

        # check modified time has not changed back
        modified_time_after = os.path.getmtime(filename)
        self.assertEqual(modified_time_before, modified_time_after)

    # 8. do backup 3, delete everything, full restore
    def testDeleteEverythingAndFullRestore(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()

        # delete all folders
        backpy.delete_temp_files(self.src_root)

        self.do_restore(chosen_index=0)

        # check folders are there
        files_in_src = os.listdir(self.src_root)
        self.assertIn('one', files_in_src)
        self.assertIn('six seven', files_in_src)

        # check correct version of changed file is restored
        self.assertEqual('yet more text', self.get_last_line(os.path.join(self.src_root, 'one', 'four', 'five')))

    # 9. do backup 4, restore the original version of the file
    def testDeleteFileAndRestoreOriginal(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()
        self.delete_one_four_five()
        self.do_backup()
        self.do_restore(['five'], chosen_index=2)

        # check file is there
        files_in_four = os.listdir(os.path.join(self.src_root, 'one', 'four'))
        self.assertIn('five', files_in_four)

        # check correct version of changed file is restored
        self.assertEqual('some text', self.get_last_line(os.path.join(self.src_root, 'one', 'four', 'five')))

    # 10. do backup 7, full restore, folder should still be deleted
    def testDeleteFolderAndFullRestore(self):
        self.do_backup()

        # create a new folder and file
        os.mkdir(os.path.join(self.src_root, 'six seven', 'twelve'))
        with open(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'a') as f:
            f.write('new file\n')

        # delete a folder
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'four'))

        self.do_backup()

        # delete all folders
        backpy.delete_temp_files(os.path.join(self.src_root))

        self.do_restore(chosen_index=0)

        # check removed folder is not there
        files_in_src = os.listdir(os.path.join(self.src_root, 'one'))
        self.assertNotIn('four', files_in_src)

        # check new file is restored
        self.assertEqual('new file', self.get_last_line(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven')))

    # 11. do backup 3, delete file, change some other files, restore intermediate version
    def testBackupDeleteChangeOtherFilesThenRestore(self):
        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()
        self.delete_one_four_five()

        # change another file
        with open(os.path.join(self.src_root, 'six seven', 'eight'), 'a') as f:
            f.write('this was changed\n')
        self.do_backup()

        # add a new file
        with open(os.path.join(self.src_root, 'one', 'eleven'), 'a') as f:
            f.write('new file\n')
        self.do_backup()

        self.do_restore(['five'], chosen_index=1)

        # check right version is restored
        expectedLastLine = 'some more text'
        actualLastLine = self.get_last_line(os.path.join(self.src_root, 'one', 'four', 'five'))
        self.assertEqual(expectedLastLine, actualLastLine)

    # 12. do backups 6 and 3 then restore a file that's been there from the start
    def testMultipleBackupsThenRestoreOriginalFile(self):
        self.do_backup()

        # create a new folder and file
        os.mkdir(os.path.join(self.src_root, 'six seven', 'twelve'))
        with open(os.path.join(self.src_root, 'six seven', 'twelve', 'eleven'), 'a') as f:
            f.write('new file\n')

        self.do_backup()
        self.change_one_four_five('some more text')
        self.do_backup()
        self.change_one_four_five('yet more text')
        self.do_backup()

        # delete a file
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'nine ten'))

        # then restore it
        self.do_restore(['nine ten'])

        # check file is there
        files_in_one = os.listdir(os.path.join(self.src_root, 'one'))
        self.assertIn('nine ten', files_in_one)


    # 13. TODO do backup and restore using UNC paths
    # should probably try this but not sure how, as user will have to set up a share prior to running test

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(RestoreTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
