"""Tests for helpers module."""

import os

from backpy.backup import TEMP_DIR
from backpy.helpers import (
    CONFIG_FILE,
    get_config_key,
    get_config_version,
    get_file_hash,
    get_filename_index,
    get_folder_index,
    handle_arg_spaces,
    list_contains,
    read_config_file,
    SKIP_KEY,
    string_contains,
    string_equals,
    string_startswith,
    update_config_file,
    write_config_file,
)
from . import common


class HelpersTest(common.BackpyTest):
    config_path = "."

    @classmethod
    def setUpClass(cls):
        super(HelpersTest, cls).setUpClass()
        cls.test_config_dict = {"default": [], "k1": ["some text"], "k2": ["more text"]}
        cls.test_config_string = "[default]\n[k1]\nsome text\n[k2]\nmore text\n"
        cls.config_path = os.path.join(TEMP_DIR, "test_config")

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls.config_path):
            os.remove(cls.config_path)

    def test_string_equals(self):
        string_1 = "some text"
        string_2 = "some text"

        self.assertTrue(string_equals(string_1, string_2))

    def test_string_does_not_equal(self):
        string_1 = "some text"
        string_2 = "some other text"

        self.assertFalse(string_equals(string_1, string_2))

    def test_string_contains(self):
        string_1 = "some"
        string_2 = "some text"

        self.assertTrue(string_contains(string_1, string_2))

    def test_string_does_not_contain(self):
        string_1 = "other"
        string_2 = "some text"

        self.assertFalse(string_contains(string_1, string_2))

    def test_string_starts_with(self):
        string_1 = "some"
        string_2 = "some text"

        self.assertTrue(string_startswith(string_1, string_2))

    def test_string_does_not_start_with(self):
        string_1 = "text"
        string_2 = "some text"

        self.assertFalse(string_startswith(string_1, string_2))

    def test_list_contains(self):
        string_1 = "a"
        list_2 = ["a", "b", "c"]

        self.assertTrue(list_contains(string_1, list_2))

    def test_list_does_not_contain(self):
        string_1 = "d"
        list_2 = ["a", "b", "c"]

        self.assertFalse(list_contains(string_1, list_2))

    def test_get_filename_index(self):
        string_1 = "b"
        list_2 = [
            os.path.join("path", "to", "a"),
            os.path.join("path", "to", "b"),
            os.path.join("path", "to", "c"),
        ]
        expected_index = 1

        actual_index = get_filename_index(string_1, list_2)
        self.assertEqual(expected_index, actual_index)

    def test_get_filename_index_is_none(self):
        string_1 = "d"
        list_2 = [
            os.path.join("path", "to", "a"),
            os.path.join("path", "to", "b"),
            os.path.join("path", "to", "c"),
        ]

        self.assertIsNone(get_filename_index(string_1, list_2))

    def test_get_folder_index(self):
        string_1 = "d"
        list_2 = [os.path.join("a", "b", "c"), os.path.join("d", "e"), os.path.join("f")]
        expected_index = 1

        actual_index = get_folder_index(string_1, list_2)
        self.assertEqual(expected_index, actual_index)

    def test_get_folder_index_is_none(self):
        string_1 = "d"
        list_2 = [
            os.path.join("path", "to", "a"),
            os.path.join("path", "to", "b"),
            os.path.join("path", "to", "c"),
        ]

        self.assertIsNone(get_folder_index(string_1, list_2))

    def test_handle_arg_spaces(self):
        src = os.path.join(self.project_dir, "resources", "source_files", "six")
        dest = os.path.join(self.dest_root, "six")
        args = ["backpy", "-a", '"' + src, 'seven"', '"' + dest, 'seven"']
        expected = ["backpy", "-a", "{} seven".format(src), "{} seven".format(dest)]

        actual = handle_arg_spaces(args)

        self.assertEqual(expected, actual)

    def test_handle_arg_spaces_mismatched_quotes(self):
        expected = ["some", '"string', 'with"', 'mismatched"', "quotes"]

        # should come back unchanged
        actual = handle_arg_spaces(expected)

        self.assertEqual(expected, actual)

    def test_get_file_hash_filename(self):
        filename = os.path.join(self.src_root, "three")
        expected_hash = "4d93d51945b88325c213640ef59fc50b"

        actual_hash = get_file_hash(filename)

        self.assertEqual(expected_hash, actual_hash)

    def test_get_file_hash_size(self):
        filename = "some file"
        filesize = 100
        expected_hash = "dee6421b215a8579c17d1704c964e1e8"

        actual_hash = get_file_hash(filename, size=filesize)

        self.assertEqual(expected_hash, actual_hash)

    def test_get_file_hash_bad_path(self):
        filename = "some file"

        self.assertIsNone(get_file_hash(filename))

    def test_get_config_version(self):
        expected_version = self.get_backpy_version()

        actual_version = get_config_version(CONFIG_FILE)

        self.assertEqual(expected_version, actual_version)

    def test_get_config_bad_version(self):
        # overwrite config with some text
        with open(CONFIG_FILE, "w+") as f:
            f.write("some text\n")

        expected_version = 0

        actual_version = get_config_version(CONFIG_FILE)

        self.assertEqual(expected_version, actual_version)

    def test_get_global_skips(self):
        expected_skips = ["*.jpg,*.tif"]

        self.add_global_skips(expected_skips)

        actual_skips = get_config_key(CONFIG_FILE, SKIP_KEY)

        self.assertCountEqual(expected_skips, actual_skips)

    def test_get_config_key_not_found(self):
        expected_value = []

        actual_value = get_config_key(CONFIG_FILE, "not found")

        self.assertCountEqual(expected_value, actual_value)

    def test_get_config_key_bad_path(self):
        expected_value = []

        actual_value = get_config_key("some file", "not found")

        self.assertCountEqual(expected_value, actual_value)

    def test_read_config_file(self):
        expected_values = self.test_config_dict
        with open(self.config_path, "w+") as f:
            f.write(self.test_config_string)

        actual_values = read_config_file(self.config_path)

        self.assertCountEqual(expected_values, actual_values)

    def test_read_config_file_bad_path(self):
        expected_values = {"default": []}

        actual_values = read_config_file("")

        self.assertCountEqual(expected_values, actual_values)

    def test_write_config_file(self):
        # turn strings into lists so order is not important
        expected_contents = self.test_config_string.split("\n")

        write_config_file(self.config_path, self.test_config_dict)
        with open(self.config_path) as f:
            actual_contents = f.read().split("\n")

        self.assertCountEqual(expected_contents, actual_contents)

    def test_write_config_file_bad_path(self):
        try:
            write_config_file("", self.test_config_dict)
        except IOError:
            self.fail("write_config_file raised an IOError!")

    def test_update_config_file(self):
        with open(self.config_path, "w+") as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.replace("more", "updated").split("\n")

        update_config_file(self.config_path, "k2", "updated text")
        with open(self.config_path) as f:
            actual_contents = f.read().split("\n")

        self.assertCountEqual(expected_contents, actual_contents)

    def test_update_config_file_new_key(self):
        with open(self.config_path, "w+") as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.split("\n")
        expected_contents.append("[k3]")
        expected_contents.append("new text")

        update_config_file(self.config_path, "k3", "new text")
        with open(self.config_path) as f:
            actual_contents = f.read().split("\n")

        self.assertCountEqual(expected_contents, actual_contents)

    def test_update_config_file_append_key(self):
        with open(self.config_path, "w+") as f:
            f.write(self.test_config_string)
        expected_contents = "{}extra text\n".format(self.test_config_string).split("\n")

        update_config_file(self.config_path, "k2", "extra text", overwrite=False)
        with open(self.config_path) as f:
            actual_contents = f.read().split("\n")

        self.assertCountEqual(expected_contents, actual_contents)

    def test_update_config_file_append_key_same_value(self):
        with open(self.config_path, "w+") as f:
            f.write(self.test_config_string)
        expected_contents = self.test_config_string.split("\n")

        update_config_file(self.config_path, "k1", "some text", overwrite=False)
        with open(self.config_path) as f:
            actual_contents = f.read().split("\n")

        self.assertCountEqual(expected_contents, actual_contents)
