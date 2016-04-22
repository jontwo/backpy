#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import glob
import os
import tempfile
import unittest
from shutil import (
    copy2,
    copytree,
)


class BackpyTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.backpy.orig')
    working_dir = '.'
    temp_dir = ''
    dest_root = ''
    src_root = ''
    do_restore = False
    timestamp = 1000

    @classmethod
    def setUpClass(cls):
        backpy.set_up_logging(0)
        # backup any existing config
        if os.path.exists(backpy.CONFIG_FILE):
            cls.do_restore = True
            if not os.path.exists(cls.config_backup):
                backpy.logger.debug('deleting existing config')
                os.rename(backpy.CONFIG_FILE, cls.config_backup)

        # set backup dirs
        cls.temp_dir = os.path.join(tempfile.gettempdir(), 'backpy')
        if not os.path.exists(cls.temp_dir):
            os.mkdir(cls.temp_dir)
        cls.src_root = os.path.join(cls.temp_dir, 'resources', 'source_files')
        cls.dest_root = os.path.join(cls.temp_dir, 'resources', 'dest_files')

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.do_restore:
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
        res_dir = os.path.join(self.temp_dir, 'resources')
        if os.path.exists(res_dir):
            backpy.delete_temp_files(res_dir)

        # copy resources
        copytree(os.path.join(self.working_dir, 'resources'), res_dir)

    # source dir - rel_path is just to test users adding relative path to
    # config file. should mostly use abs path (the files that were copied
    # to temp folder) so files can be altered if needed
    def add_one_folder(self, rel_path=False):
        if rel_path:
            src = os.path.join(self.working_dir, 'resources', 'source_files', 'one')
        else:
            src = os.path.join(self.src_root, 'one')
        dest = os.path.join(self.dest_root, 'one')
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def add_six_seven_folder(self, rel_path=False):
        if rel_path:
            src = os.path.join(self.working_dir, 'resources', 'source_files', 'six seven')
        else:
            src = os.path.join(self.src_root, 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def text_in_file(self, filename, text):
        with open(filename) as l:
            config_contents = l.read()
            return text in config_contents

    def get_file_size(self, filename):
        size = 0
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        return size

    def count_files(self, search_path):
        return len(glob.glob(search_path))
