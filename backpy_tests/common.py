#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import glob
import os
import unittest
from shutil import (
    copy2,
    copytree,
)


class BackpyTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.backpy.orig')
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_root = ''
    src_root = ''
    restore_config = False
    timestamp = 1000

    @classmethod
    def setUpClass(cls):
        backpy.set_up_logging(0)
        # backup any existing config
        if os.path.exists(backpy.CONFIG_FILE):
            cls.restore_config = True
            if not os.path.exists(cls.config_backup):
                backpy.logger.debug('deleting existing config')
                os.rename(backpy.CONFIG_FILE, cls.config_backup)

        # set backup dirs
        if not os.path.exists(backpy.TEMP_DIR):
            os.mkdir(backpy.TEMP_DIR, 0o777)
        cls.src_root = os.path.join(backpy.TEMP_DIR, 'resources', 'source_files')
        cls.dest_root = os.path.join(backpy.TEMP_DIR, 'resources', 'dest_files')

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.restore_config:
            backpy.logger.debug('restoring config')
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    @classmethod
    def mock_timestamp(cls):
        # datetime.now is the same for all unit tests, so use an incrementing value instead
        cls.timestamp += 1
        return cls.timestamp

    def setUp(self):
        backpy.logger.debug('starting test {}'.format(unittest.TestCase.id(self)))
        # start test with blank config
        if os.path.exists(backpy.CONFIG_FILE):
            os.unlink(backpy.CONFIG_FILE)
        backpy.init(backpy.CONFIG_FILE)

        # and blank resource dir
        res_dir = os.path.join(backpy.TEMP_DIR, 'resources')
        if os.path.exists(res_dir):
            backpy.delete_temp_files(res_dir)

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
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def add_six_seven_folder(self, rel_path=False):
        if rel_path:
            src = os.path.join(self.project_dir, 'resources', 'source_files', 'six seven')
        else:
            src = os.path.join(self.src_root, 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def text_in_file(self, filename, text):
        with open(filename) as l:
            file_contents = l.read()
            return text in file_contents

    def get_last_line(self, filename):
        with open(filename, 'r') as f:
            lines = f.read().strip().split('\n')
        return lines[-1] if lines else ''

    def get_file_size(self, filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        return size

    def count_files(self, search_path):
        return len(glob.glob(search_path))

    # backup/restore methods for use in more than one test
    def do_backup(self):
        for directory in backpy.read_directory_list(backpy.CONFIG_FILE):
            backpy.perform_backup(directory, self.mock_timestamp())

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
        backpy.delete_temp_files(filepath)

    # delete a file
    def delete_one_four_five(self):
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'four', 'five'))

    def delete_one_nine_ten(self):
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'nine ten'))

    # delete a folder
    def delete_one_four(self):
        backpy.delete_temp_files(os.path.join(self.src_root, 'one', 'four'))

    # delete a folder
    def delete_six_seven(self):
        backpy.delete_temp_files(os.path.join(self.src_root, 'six seven'))

    def delete_all_folders(self):
        backpy.delete_temp_files(self.src_root)

    def do_restore(self, files=None, chosen_index=None):
        backpy.perform_restore(backpy.read_directory_list(backpy.CONFIG_FILE), files, chosen_index)

    def create_folder(self, folderpath):
        backpy.logger.debug('creating folder {0}'.format(folderpath))
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
