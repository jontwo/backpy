#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import glob
import os
import unittest
from shutil import copy2


class BackpyTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.backpy.orig')
    root_dir = '.'
    do_restore = False

    @classmethod
    def setUpClass(cls):
        # backup any existing config
        if os.path.exists(backpy.CONFIG_FILE):
            if os.path.exists(cls.config_backup):
                # delete old backup
                os.unlink(cls.config_backup)
            os.rename(backpy.CONFIG_FILE, cls.config_backup)
            backpy.set_up_logging(0)
            cls.do_restore = True

        # set root backup dir
        if os.getenv("OS") == "Windows_NT":
            cls.dest_root = os.path.join(
                backpy.ROOT_PATH, 'temp', 'backpy'
            )
        else:
            cls.dest_root = os.path.join(
                backpy.ROOT_PATH, 'tmp', 'backpy'
            )
        if not os.path.exists(cls.dest_root):
            os.mkdir(cls.dest_root)

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.do_restore:
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    def setUp(self):
        # start test with blank config
        if os.path.exists(backpy.CONFIG_FILE):
            os.unlink(backpy.CONFIG_FILE)
        backpy.init(backpy.CONFIG_FILE)

    def add_one_folder(self):
        src = os.path.join(self.root_dir, 'resources', 'source_files', 'one')
        dest = os.path.join(self.dest_root, 'one')
        backpy.add_directory(backpy.CONFIG_FILE, src, dest)

    def add_six_seven_folder(self):
        src = os.path.join('resources', 'source_files', 'six seven')
        dest = os.path.join(self.dest_root, 'six seven')
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.root_dir, src), dest
        )

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
