"""Tests for file_index module."""

import os

from backpy.backpy import add_global_skip
from backpy.backup import TEMP_DIR
from backpy.file_index import FileIndex
from backpy.helpers import CONFIG_FILE, get_file_hash, is_osx, is_windows
from .common import BackpyTest


class IndexTest(BackpyTest):
    index = None

    @classmethod
    def setUpClass(cls):
        super(IndexTest, cls).setUpClass()

        # create index
        cls.index = FileIndex(cls.src_root)
        cls.index.gen_index()

        # index file from backpy v1.4.7
        cls.index_147 = os.path.join(TEMP_DIR, "resources", "index_147")

        # index file from backpy v1.5.0
        cls.index_150 = os.path.join(TEMP_DIR, "resources", "index_150")

    def list_all_files(self):
        return [
            os.path.join(self.src_root, "three"),
            os.path.join(self.src_root, "one", "nine ten"),
            os.path.join(self.src_root, "one", "four", "five"),
            os.path.join(self.src_root, "six seven", "eight"),
        ]

    def list_all_dirs(self):
        return [
            self.src_root,
            os.path.join(self.src_root, "one"),
            os.path.join(self.src_root, "one", "four"),
            os.path.join(self.src_root, "six seven"),
        ]

    def replace_index_paths(self, index_text, is_str=False):
        """Saved index files contain linux paths, replace them if running tests on another OS."""
        if is_str:
            index_text = index_text.split("\n")
        index_text = [
            f.replace("/tmp/backpy/resources/source_files", self.src_root) for f in index_text
        ]
        if is_windows():
            index_text = [f.replace("/", "\\") for f in index_text]
        # Remove duplicates
        index_text = sorted(set(index_text))
        return "\n".join(index_text) if is_str else index_text

    def test_list_files(self):
        expected_files = self.list_all_files()

        actual_files = self.index.files()

        self.assertCountEqual(expected_files, actual_files)

    def test_list_dirs(self):
        expected_dirs = self.list_all_dirs()

        actual_dirs = self.index.dirs()

        self.assertCountEqual(expected_dirs, actual_dirs)

    def test_skips(self):
        # create fresh index with exclusions
        expected_rules = ["a", "b", "c"]
        index = FileIndex(self.src_root, exclusion_rules=expected_rules)

        actual_rules = index.skips()

        self.assertCountEqual(expected_rules, actual_rules)

    def test_global_skips(self):
        # create fresh index with exclusions
        initial_rules = ["a", "b", "c"]
        added_rules = ["d,e"]
        expected_rules = ["a", "b", "c", "d", "e"]
        add_global_skip(CONFIG_FILE, added_rules)
        index = FileIndex(self.src_root, exclusion_rules=initial_rules)

        actual_rules = index.skips()

        self.assertCountEqual(expected_rules, actual_rules)

    def test_is_valid_bad_file(self):
        self.assertFalse(self.index.is_valid("bad file"))

    def test_is_valid_no_rules(self):
        self.assertTrue(self.index.is_valid(self.get_one_four_five_path()))

    def test_is_valid_skipped_file(self):
        # create fresh index with one exclusion
        expected_rules = ["*four*"]
        index = FileIndex(self.src_root, exclusion_rules=expected_rules)

        self.assertFalse(index.is_valid(self.get_one_four_five_path()))

    def test_hash_exact_path(self):
        expected_hash = get_file_hash(self.get_one_four_five_path())

        actual_hash = self.index.file_hash(self.get_one_four_five_path())

        self.assertEqual(expected_hash, actual_hash)

    def test_hash_exact_path_not_found(self):
        actual_hash = self.index.file_hash("bad file")

        self.assertIsNone(actual_hash)

    def test_hash_name_only(self):
        expected_hash = get_file_hash(self.get_one_four_five_path())

        actual_hash = self.index.file_hash("five", exact_match=False)

        self.assertEqual(expected_hash, actual_hash)

    def test_hash_name_only_not_found(self):
        actual_hash = self.index.file_hash("bad file", exact_match=False)

        self.assertIsNone(actual_hash)

    def test_is_folder_exact_path(self):
        self.assertTrue(self.index.is_folder(self.src_root))

    def test_is_folder_exact_path_not_found(self):
        self.assertFalse(self.index.is_folder("bad folder"))

    def test_is_folder_name_only(self):
        self.assertTrue(self.index.is_folder("source_files", exact_match=False))

    def test_is_folder_name_only_not_found(self):
        self.assertFalse(self.index.is_folder("bad folder", exact_match=False))

    def test_get_diff_no_index(self):
        expected_diff = self.list_all_files()

        actual_diff = self.index.get_diff()

        self.assertCountEqual(expected_diff, actual_diff)

    def test_get_diff_no_change(self):
        expected_diff = []

        actual_diff = self.index.get_diff(self.index)

        self.assertEqual(expected_diff, actual_diff)

    def test_get_diff_changed_file(self):
        expected_diff = [self.get_one_four_five_path()]
        # change a file and regenerate index
        self.change_one_four_five("some text")
        new_index = FileIndex(self.src_root)
        new_index.gen_index()

        actual_diff = self.index.get_diff(new_index)

        self.assertEqual(expected_diff, actual_diff)

    def test_get_diff_deleted_file(self):
        expected_diff = [self.get_one_four_five_path()]
        # delete a file and regenerate index
        self.delete_one_four_five()
        new_index = FileIndex(self.src_root)
        new_index.gen_index()

        actual_diff = self.index.get_diff(new_index)

        self.assertEqual(expected_diff, actual_diff)

    def test_get_missing_no_index(self):
        expected_missing = []

        actual_missing = self.index.get_missing()

        self.assertEqual(expected_missing, actual_missing)

    def test_get_missing_no_change(self):
        expected_missing = []

        actual_missing = self.index.get_missing(self.index)

        self.assertEqual(expected_missing, actual_missing)

    def test_get_missing_deleted_file(self):
        expected_missing = [self.get_one_four_five_path()]
        # delete a file and regenerate index
        self.delete_one_four_five()
        new_index = FileIndex(self.src_root)
        new_index.gen_index()

        actual_missing = new_index.get_missing(self.index)

        self.assertEqual(expected_missing, actual_missing)

    def test_write_index(self):
        expected_text = self.file_contents(self.index_147)
        tmp_path = os.path.join(TEMP_DIR, ".{}_index".format(self.timestamp))

        self.index.write_index(tmp_path)
        actual_text = self.file_contents(tmp_path)
        if is_windows() or is_osx():
            expected_text = self.replace_index_paths(expected_text, is_str=True)
        self.assertCountEqual(expected_text, actual_text)

    def test_read_index(self):
        # create a new index and read existing (old style) index file
        index = FileIndex(self.src_root)
        index.read_index(self.index_147)

        # check files and dirs
        expected_files = self.list_all_files()
        actual_files = index.files()
        if is_windows() or is_osx():
            actual_files = self.replace_index_paths(actual_files)
        self.assertCountEqual(expected_files, actual_files)

        expected_dirs = self.list_all_dirs()
        actual_dirs = index.dirs()
        if is_windows() or is_osx():
            actual_dirs = self.replace_index_paths(actual_dirs)
        self.assertCountEqual(expected_dirs, actual_dirs)

    def test_read_index_not_found(self):
        # create a new index and try to read non-existant index file
        index = FileIndex(self.src_root)
        index.read_index()

        # check files and dirs
        expected_files = []
        actual_files = index.files()
        self.assertCountEqual(expected_files, actual_files)

        # source is always added
        expected_dirs = [self.src_root]
        actual_dirs = index.dirs()
        self.assertCountEqual(expected_dirs, actual_dirs)

    def test_read_index150(self):
        # create a new index and read existing (new style) index file
        # headings should be ignored, except files and dirs
        index = FileIndex(self.src_root)
        index.read_index(self.index_150)

        # check files and dirs
        expected_files = self.list_all_files()
        actual_files = index.files()
        if is_windows() or is_osx():
            actual_files = self.replace_index_paths(actual_files)
        self.assertCountEqual(expected_files, actual_files)

    def test_read_index_check_adb(self):
        # create a new index and read existing (new style) index file
        index = FileIndex(self.src_root)
        index.read_index(self.index_150)

        self.assertFalse(index.__adb__)
