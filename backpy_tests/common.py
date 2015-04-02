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
    rmtree,
)


class BackpyTest(unittest.TestCase):
    config_backup = os.path.expanduser('~/.backpy.orig')
    working_dir = '.'
    temp_dir = ''
    dest_root = ''
    src_root = ''
    do_restore = False

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
        res_dir = os.path.join(cls.temp_dir, 'resources')
        if os.path.exists(res_dir):
            rmtree(cls.temp_dir, ignore_errors=True)
        cls.src_root = os.path.join(cls.temp_dir, 'resources', 'source_files')
        cls.dest_root = os.path.join(cls.temp_dir, 'resources', 'dest_files')

        # copy resources
        copytree(os.path.join(cls.working_dir, 'resources'), res_dir)

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        copy2(backpy.CONFIG_FILE, cls.dest_root)
        # restore config
        if cls.do_restore:
            backpy.logger.debug('restoring config')
            os.unlink(backpy.CONFIG_FILE)
            os.rename(cls.config_backup, backpy.CONFIG_FILE)

    def setUp(self):
        # start test with blank config
        if os.path.exists(backpy.CONFIG_FILE):
            os.unlink(backpy.CONFIG_FILE)
        backpy.init(backpy.CONFIG_FILE)

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
        backpy.add_directory(
            backpy.CONFIG_FILE, os.path.join(self.working_dir, src), dest
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
