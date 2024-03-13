"""Tests for backup function."""

import os
import unittest
from datetime import datetime

from backpy.backpy import add_skip
from backpy.backup import Backup
from backpy.helpers import CONFIG_FILE, delete_temp_files, is_windows
from .common import BackpyTest


class BackupTest(BackpyTest):

    def setUp(self):
        # start test with blank config
        super(BackupTest, self).setUp()
        # clear dest folder
        delete_temp_files(self.dest_root)
        # add some entries to config
        self.add_global_skips("*.jpg,*.tif")
        self.add_one_folder()
        self.add_six_seven_folder()
        self.one_folder = os.path.join(self.dest_root, "one")
        self.six_seven_folder = os.path.join(self.dest_root, "six seven")

    # 1. perform backup into an empty destination folder
    def test_initial_backup(self):
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 1)

    # 2. do 1, change a file, backup again
    def test_second_backup(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 1)

    # 3. do 2, change a file, backup again
    def test_third_backup(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 3)
        self.assertEqual(zips_in_six_seven, 1)

    # 4. do 3, delete the file, backup again
    def test_delete_file_and_backup(self):
        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()
        self.change_one_four_five("yet more text")
        self.do_backup()

        # delete file
        self.delete_one_four_five()

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 4)
        self.assertEqual(zips_in_six_seven, 1)

    # 5. do 1, add a new file, backup again
    def test_add_new_file_and_backup(self):
        self.do_backup()

        self.create_file(os.path.join(self.src_root, "six seven", "eleven"), "new file\n")

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 6. do 1, add a folder, backup again
    def test_add_new_folder_and_backup(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, "six seven", "twelve"))
        self.create_file(os.path.join(self.src_root, "six seven", "twelve", "eleven"), "new file\n")

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    # 7. do 6, delete a different folder, backup again
    def test_delete_folder_and_backup(self):
        self.do_backup()

        self.create_folder(os.path.join(self.src_root, "six seven", "twelve"))
        self.create_file(os.path.join(self.src_root, "six seven", "twelve", "eleven"), "new file\n")

        # delete a folder
        self.delete_one_four()

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 2)

    # 8. do 1 (with a skip), change a file in skipped folder, backup again
    def test_add_skip_and_backup(self):
        # add skip
        skips = [
            os.path.join(self.src_root, "one"),
            os.path.join(self.dest_root, "one"),
            os.path.join(self.src_root, "one", "four"),
        ]
        add_skip(CONFIG_FILE, skips)

        self.do_backup()
        self.change_one_four_five("some more text")
        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 1)

    # 9. do 1 (with a wildcard skip), change a file in skipped folder, backup again
    def test_add_skip_with_wildcard(self):
        # add skip
        skips = [
            os.path.join(self.src_root, "six seven"),
            os.path.join(self.dest_root, "six seven"),
            "seven",
        ]
        add_skip(CONFIG_FILE, skips, True)

        self.do_backup()

        self.create_file(os.path.join(self.src_root, "six seven", "eight"), "some more text\n")

        self.do_backup()

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, "*.tar.gz"))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 0)

    # 10. do 1, add skipped file, backup again
    def test_backup_with_global_skip(self):
        self.do_backup()
        zips_before = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))

        self.create_file(os.path.join(self.src_root, "one", "test.jpg"), "0\n")

        self.do_backup()
        zips_after = self.count_files(os.path.join(self.one_folder, "*.tar.gz"))

        self.assertEqual(zips_before, 1)
        self.assertEqual(zips_before, zips_after)

    def test_get_timestamp(self):
        """Test timestamp method"""
        expected = datetime.now().strftime("%Y%m%d%H%M%S")
        actual = Backup.get_timestamp()
        self.assertEqual(expected, actual)

    @unittest.skipUnless(is_windows(), "Windows only")
    def test_get_member_name_windows(self):
        filepath = "c:\\path\\to\\member"
        expected = ("c:\\", "path/to/member")
        actual = Backup.get_member_name(filepath)
        self.assertEqual(expected, actual)

    @unittest.skipIf(is_windows(), "*nix only")
    def test_get_member_name_unix(self):
        filepath = "/path/to/member"
        expected = ("/", "path/to/member")
        actual = Backup.get_member_name(filepath)
        self.assertEqual(expected, actual)
