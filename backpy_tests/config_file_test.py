"""Config file tests."""

import os

import backpy
from backpy.helpers import SKIP_KEY, get_config_key
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
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        src = 'test'
        dest = self.dest_root
        backpy.add_directory(
            backpy.CONFIG_FILE, src, dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertEqual(size_before, size_after)

    # try to add a folder that does exist
    # check source path is added to config file
    def test_add_folder_source_found(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'one')
        dest = os.path.join(self.dest_root, 'one')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to add a folder that contains spaces in the name
    def test_add_folder_with_spaces(self):
        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertGreater(size_after, size_before)
        self.assertTrue(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to remove a folder
    def test_remove_folder(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(backpy.CONFIG_FILE)
        # use rel path for source so can search config file for text
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.delete_directory(
            backpy.CONFIG_FILE, os.path.join(self.project_dir, src), dest, False
        )

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to remove a folder with a valid index
    def test_remove_folder_by_index(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(backpy.CONFIG_FILE)
        src = os.path.join('resources', 'source_files', 'six seven')
        dirlist = backpy.read_directory_list(backpy.CONFIG_FILE)
        backpy.delete_directory_by_index(backpy.CONFIG_FILE, 1, dirlist, False)

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertLess(size_after, size_before)
        self.assertFalse(self.text_in_file(backpy.CONFIG_FILE, src))

    # try to remove a folder with an invalid index
    def test_remove_folder_bad_index(self):
        # add some entries to config
        self.add_one_folder()
        self.add_six_seven_folder(True)

        size_before = self.get_file_size(backpy.CONFIG_FILE)
        dirlist = backpy.read_directory_list(backpy.CONFIG_FILE)
        backpy.delete_directory_by_index(backpy.CONFIG_FILE, 2, dirlist, False)

        size_after = self.get_file_size(backpy.CONFIG_FILE)
        self.assertEqual(size_after, size_before)

    def test_add_global_skip_as_string(self):
        expected_skips = ['1,2,3']

        backpy.add_global_skip(backpy.CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_add_global_skip_with_wildcards(self):
        expected_skips = ['*.abc,*.def']

        backpy.add_global_skip(backpy.CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_append_global_skip(self):
        expected_skips = ['one,two,three']
        backpy.add_global_skip(backpy.CONFIG_FILE, ['one,two'])
        backpy.add_global_skip(backpy.CONFIG_FILE, ['two,three'])

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_add_global_skip_as_items(self):
        expected_skips = ['1', '2', '3']

        backpy.add_global_skip(backpy.CONFIG_FILE, expected_skips)

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual([','.join(expected_skips)], actual_skips)

    def test_remove_global_skip(self):
        added_skips = ['1,2,3,4']
        expected_skips = ['1,3,4']
        backpy.add_global_skip(backpy.CONFIG_FILE, added_skips)

        backpy.delete_global_skip(backpy.CONFIG_FILE, ['2'])

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_remove_global_skips(self):
        added_skips = ['1,2,3,4']
        removed_skips = ['2', '3', '4']
        expected_skips = ['1']
        backpy.add_global_skip(backpy.CONFIG_FILE, added_skips)

        backpy.delete_global_skip(backpy.CONFIG_FILE, removed_skips)

        actual_skips = get_config_key(backpy.CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)
