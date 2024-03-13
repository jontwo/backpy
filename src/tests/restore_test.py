"""Tests for restore function."""

import os

from backpy.backpy import perform_restore
from backpy.backup import Backup, TEMP_DIR
from backpy.helpers import delete_temp_files
from . import common


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
        delete_temp_files(self.dest_root)
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder()

    # 1. do backup 1, delete 1 file, restore the file by full path
    def test_restore_one_file_full_path(self):
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore([self.get_one_four_five_path()], 0)

        # check file is there
        self.assertIn("five", self.get_files_in_four())

    # 2. do backup 1, delete 1 file, restore the file by name only
    def test_restore_one_file_by_name(self):
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore(["five"], 0)

        # check file is there
        self.assertIn("five", self.get_files_in_four())

    # 3. do backup 1, delete file, full restore
    def test_full_restore_one_file_deleted(self):
        self.do_backup()
        self.delete_one_four_five()
        self.do_restore(chosen_index=0)

        # check file is there
        self.assertIn("five", self.get_files_in_four())

    # 4. do backup 1, delete folder, restore the folder by full path
    def test_restore_one_folder_by_full_path(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore([self.get_six_seven_path()])

        # check folder is there
        self.assertIn("six seven", self.get_files_in_src())

    # 5. do backup 1, delete folder, restore the folder by name only
    def test_restore_one_folder_by_name(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore(["six seven"])

        # check folder is there
        self.assertIn("six seven", self.get_files_in_src())

    # 6. do backup 1, delete folder, full restore
    def test_full_restore_one_folder_deleted(self):
        self.do_backup()
        self.delete_six_seven()
        self.do_restore(chosen_index=0)

        # check folder is there
        self.assertIn("six seven", self.get_files_in_src())

    # 7. do backup 1, restore a file, should be skipped as file is not changed
    def test_restore_one_file_unchanged(self):
        self.do_backup()

        # change file timestamp wihout changing contents
        filename = os.path.join(self.src_root, "one", "nine ten")
        self.change_file_timestamp(filename)
        modified_time_before = os.path.getmtime(filename)

        self.do_restore(["nine ten"], 0)

        # check modified time has not changed back
        modified_time_after = self.get_file_timestamp(filename)
        self.assertEqual(modified_time_before, modified_time_after)

    # 8. do backup 3, delete everything, full restore
    def test_delete_everything_and_full_restore(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()

        self.delete_all_folders()
        self.do_restore(chosen_index=0)

        # check folders are there
        self.assertIn("one", self.get_files_in_src())
        self.assertIn("six seven", self.get_files_in_src())

        # check correct version of changed file is restored
        self.assertEqual(
            "yet more text", self.get_last_line(os.path.join(self.src_root, "one", "four", "five"))
        )

    # 9. do backup 4, restore the original version of the file
    def test_delete_file_and_restore_original(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()
        self.delete_one_four_five()
        self.do_backup()
        self.do_restore(["five"], chosen_index=2)

        # check file is there
        self.assertIn("five", self.get_files_in_four())

        # check correct version of changed file is restored
        self.assertEqual(
            "some text", self.get_last_line(os.path.join(self.src_root, "one", "four", "five"))
        )

    # 10. do backup 7, full restore, folder should still be deleted
    def test_delete_folder_and_full_restore(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, "six seven", "twelve"))
        self.create_file(os.path.join(self.src_root, "six seven", "twelve", "eleven"), "new file\n")

        self.delete_one_four()
        self.do_backup()

        self.delete_all_folders()
        self.do_restore(chosen_index=0)

        # check removed folder is not there
        self.assertNotIn("four", self.get_files_in_src())

        # check new file is restored
        self.assertEqual(
            "new file",
            self.get_last_line(os.path.join(self.src_root, "six seven", "twelve", "eleven")),
        )

    # 11. do backup 3, delete file, change some other files, restore intermediate version
    def test_backup_delete_change_other_files_then_restore(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()
        self.delete_one_four_five()

        self.create_file(os.path.join(self.src_root, "six seven", "eight"), "this was changed\n")
        self.do_backup()

        self.create_file(os.path.join(self.src_root, "one", "eleven"), "new file\n")
        self.do_backup()

        self.do_restore(["five"], chosen_index=1)

        # check right version is restored
        expected_last_line = "some more text"
        actual_last_line = self.get_last_line(os.path.join(self.src_root, "one", "four", "five"))
        self.assertEqual(expected_last_line, actual_last_line)

    # 12. do backups 6 and 3 then restore a file that's been there from the start
    def test_multiple_backups_then_restore_original_file(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, "six seven", "twelve"))
        self.create_file(os.path.join(self.src_root, "six seven", "twelve", "eleven"), "new file\n")

        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()

        # delete a file
        self.delete_one_nine_ten()

        # then restore it
        self.do_restore(["nine ten"])

        # check file is there
        self.assertIn("nine ten", self.get_files_in_one())

    # restore a file to a different location
    def test_restore_file_to_temp_path(self):
        self.do_backup()

        # original file path and contents
        orig_path = os.path.join(self.src_root, "one", "nine ten")
        expected_text = "more text"
        # file location inside zip
        _, zip_path = Backup.get_member_name(orig_path)
        # new restore path
        restore_dir = os.path.join(TEMP_DIR, "resources", "alt_restore_dir")

        # restore file to alternate path
        perform_restore(
            [["", os.path.join(self.dest_root, "one")]],
            files=["nine ten"],
            restore_path=restore_dir,
        )

        # check restored file contents
        actual_text = self.file_contents(os.path.join(restore_dir, zip_path))
        self.assertEqual(expected_text, actual_text)

    # restore a folder to a different location
    def test_restore_folder_to_temp_path(self):
        self.do_backup()

        # original folder path and file contents
        orig_path = os.path.join(self.src_root, "six seven")
        expected_text = "text"
        # file location inside zip
        _, zip_path = Backup.get_member_name(orig_path)
        # new restore path
        restore_dir = os.path.join(TEMP_DIR, "resources", "alt_restore_dir")

        # restore file to alternate path
        perform_restore([["", os.path.join(self.dest_root, "six seven")]], restore_path=restore_dir)

        # check restored file contents
        actual_text = self.file_contents(os.path.join(restore_dir, zip_path, "eight"))
        self.assertEqual(expected_text, actual_text)
