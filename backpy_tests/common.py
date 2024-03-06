"""Common test functions."""

import glob
import logging
import os
import unittest
from shutil import copy2, copytree

from backpy.backpy import (
    add_directory, add_global_skip, init, perform_backup, perform_restore, read_directory_list
)
from backpy.backup import TEMP_DIR
from backpy.helpers import CONFIG_FILE, delete_temp_files
from backpy.logger import LOG_NAME, set_up_logging

LOG = logging.getLogger(LOG_NAME)


class BackpyTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.orig')
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_root = ''
    src_root = ''
    restore_config = False
    timestamp = 1000

    @classmethod
    def shortDescription(cls):
        """Stop nose writing docstrings instead of test names."""
        pass

    @classmethod
    def setUpClass(cls):
        set_up_logging(0)
        logging.disable(logging.CRITICAL)
        # backup any existing config
        if os.path.exists(CONFIG_FILE):
            cls.restore_config = True
            if not os.path.exists(cls.config_backup):
                LOG.debug('deleting existing config')
                os.rename(CONFIG_FILE, cls.config_backup)

        # set backup dirs
        if not os.path.exists(TEMP_DIR):
            os.mkdir(TEMP_DIR, 0o777)
        cls.src_root = os.path.join(TEMP_DIR, 'resources', 'source_files')
        cls.dest_root = os.path.join(TEMP_DIR, 'resources', 'dest_files')

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.restore_config:
            LOG.debug('restoring config')
            os.unlink(CONFIG_FILE)
            os.rename(cls.config_backup, CONFIG_FILE)
        logging.disable(logging.NOTSET)

    @classmethod
    def mock_timestamp(cls):
        # datetime.now is the same for all unit tests, so use an incrementing value instead
        cls.timestamp += 1
        return cls.timestamp

    def setUp(self):
        LOG.debug('starting test %s', unittest.TestCase.id(self))
        # start test with blank config
        if os.path.exists(CONFIG_FILE):
            os.unlink(CONFIG_FILE)
        init(CONFIG_FILE)

        # and blank resource dir
        res_dir = os.path.join(TEMP_DIR, 'resources')
        if os.path.exists(res_dir):
            delete_temp_files(res_dir)

        # copy resources
        copytree(os.path.join(self.project_dir, 'resources'), res_dir)

    # source dir - rel_path is just to test users adding relative path to
    # config file. should mostly use abs path (the files that were copied
    # to temp folder) so files can be altered if needed
    def add_one_folder(self, rel_path=False):
        if rel_path:
            src = os.path.join(self.project_dir, 'resources', 'source_files', 'one')
        else:
            src = os.path.join(self.src_root, 'one')
        dest = os.path.join(self.dest_root, 'one')
        add_directory(CONFIG_FILE, src, dest)

    def add_six_seven_folder(self, rel_path=False):
        if rel_path:
            src = os.path.join(self.project_dir, 'resources', 'source_files', 'six seven')
        else:
            src = os.path.join(self.src_root, 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        add_directory(CONFIG_FILE, src, dest)

    @staticmethod
    def add_global_skips(skips):
        add_global_skip(CONFIG_FILE, skips)

    @staticmethod
    def file_contents(filename):
        with open(filename) as fp:
            return fp.read().strip()

    def text_in_file(self, filename, text):
        return text in self.file_contents(filename)

    def get_last_line(self, filename):
        with open(filename, 'r') as f:
            lines = f.read().strip().split('\n')
        return lines[-1] if lines else ''

    @staticmethod
    def get_file_size(filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        return size

    @staticmethod
    def count_files(search_path):
        return len(glob.glob(search_path))

    # backup/restore methods for use in more than one test
    def do_backup(self):
        for directory in read_directory_list(CONFIG_FILE):
            perform_backup(directory, self.mock_timestamp())

    def get_files_in_src(self):
        return os.listdir(self.src_root)

    def get_files_in_one(self):
        return os.listdir(os.path.join(self.src_root, 'one'))

    def get_files_in_four(self):
        return os.listdir(os.path.join(self.src_root, 'one', 'four'))

    def get_one_four_five_path(self):
        return os.path.join(self.src_root, 'one', 'four', 'five')

    def get_six_seven_path(self):
        return os.path.join(self.src_root, 'six seven')

    # add text to a file
    def change_one_four_five(self, text):
        with open(os.path.join(self.src_root, 'one', 'four', 'five'), 'a') as f:
            f.write('{0}\n'.format(text))

    # generic file delete method
    def delete_files(self, filepath):
        delete_temp_files(filepath)

    # delete a file
    def delete_one_four_five(self):
        delete_temp_files(os.path.join(self.src_root, 'one', 'four', 'five'))

    def delete_one_nine_ten(self):
        delete_temp_files(os.path.join(self.src_root, 'one', 'nine ten'))

    # delete a folder
    def delete_one_four(self):
        delete_temp_files(os.path.join(self.src_root, 'one', 'four'))

    # delete a folder
    def delete_six_seven(self):
        delete_temp_files(os.path.join(self.src_root, 'six seven'))

    def delete_all_folders(self):
        delete_temp_files(self.src_root)

    def do_restore(self, files=None, chosen_index=None):
        perform_restore(read_directory_list(CONFIG_FILE), files, chosen_index)

    def create_folder(self, folderpath):
        LOG.debug('creating folder %s', folderpath)
        os.mkdir(folderpath)

    def create_file(self, filepath, text):
        with open(filepath, 'a') as f:
            f.write(text)

    def get_file_timestamp(self, filename):
        return os.path.getmtime(filename)

    def change_file_timestamp(self, filename):
        with open(filename, 'r') as f:
            file_content = f.read()
        with open(filename, 'w') as f:
            f.write(file_content)

    def get_backpy_version(self):
        for line in open(os.path.join(self.project_dir, 'backpy', 'backpy.py')):
            if '__version__ = ' in line:
                return eval(line.split('=')[-1])
