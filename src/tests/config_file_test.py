"""Config file tests."""

import os

from backpy.backpy import (
    add_directory,
    add_global_skip,
    delete_directory,
    delete_directory_by_index,
    delete_global_skip,
    read_directory_list,
)
from backpy.helpers import CONFIG_FILE, get_config_key, SKIP_KEY
from . import common


class ConfigTest(common.BackpyTest):
    @classmethod
    def setUpClass(cls):
        # backup any existing config
        # set root backup dir
        super(ConfigTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(ConfigTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(ConfigTest, self).setUp()

    # try to add a folder that does not exist
    # and check nothing is added to config file
    def test_add_folder_source_not_found(self):
        size_before = self.get_file_size(CONFIG_FILE)
        src = "test"
        dest = self.dest_root
        add_directory(CONFIG_FILE, src, dest)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertEqual(size_before, size_after)

    # try to add a folder that does exist
    # check source path is added to config file
    def test_add_folder_source_found(self):
        size_before = self.get_file_size(CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join("resources", "source_files", "one")
        dest = os.path.join(self.dest_root, "one")
        add_directory(CONFIG_FILE, os.path.join(self.project_dir, src), dest)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name
    def test_add_folder_with_spaces(self):
        size_before = self.get_file_size(CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join("resources", "source_files", "six seven")
        dest = os.path.join(self.dest_root, "six seven")
        add_directory(CONFIG_FILE, os.path.join(self.project_dir, src), dest)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(CONFIG_FILE, src))

    # try to remove a folder
    def test_remove_folder(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join("resources", "source_files", "six seven")
        dest = os.path.join(self.dest_root, "six seven")
        delete_directory(CONFIG_FILE, os.path.join(self.project_dir, src), dest, False)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(CONFIG_FILE, src))

    # try to remove a folder with a valid index
    def test_remove_folder_by_index(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(CONFIG_FILE)
        src = os.path.join("resources", "source_files", "six seven")
        dirlist = read_directory_list(CONFIG_FILE)
        delete_directory_by_index(CONFIG_FILE, 1, dirlist, False)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(CONFIG_FILE, src))

    # try to remove a folder with an invalid index
    def test_remove_folder_bad_index(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(CONFIG_FILE)
        dirlist = read_directory_list(CONFIG_FILE)
        delete_directory_by_index(CONFIG_FILE, 2, dirlist, False)

        size_after = self.get_file_size(CONFIG_FILE)
        self.assertEqual(size_after, size_before)

    def test_add_global_skip_as_string(self):
        expected_skips = ["1,2,3"]

        add_global_skip(CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_add_global_skip_with_wildcards(self):
        expected_skips = ["*.abc,*.def"]

        add_global_skip(CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_append_global_skip(self):
        expected_skips = ["one,two,three"]
        add_global_skip(CONFIG_FILE, ["one,two"])
        add_global_skip(CONFIG_FILE, ["two,three"])

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_add_global_skip_as_items(self):
        expected_skips = ["1", "2", "3"]

        add_global_skip(CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual([",".join(expected_skips)], actual_skips)

    def test_remove_global_skip(self):
        added_skips = ["1,2,3,4"]
        expected_skips = ["1,3,4"]
        add_global_skip(CONFIG_FILE, added_skips)

        delete_global_skip(CONFIG_FILE, ["2"])

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_remove_global_skips(self):
        added_skips = ["1,2,3,4"]
        removed_skips = ["2", "3", "4"]
        expected_skips = ["1"]
        add_global_skip(CONFIG_FILE, added_skips)

        delete_global_skip(CONFIG_FILE, removed_skips)

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)
