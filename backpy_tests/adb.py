#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import common
import os
import platform
import subprocess
import unittest


class AdbTest(common.BackpyTest):
    @classmethod
    def setUpClass(cls):
        # check adb is installed and one device is connected
        adb_exe = 'adb.exe' if platform.system() == 'Windows' else 'adb'
        got_adb = False
        for folder in os.getenv('PATH').split(os.pathsep):
            if os.path.exists(os.path.join(folder, adb_exe)):
                got_adb = True
                break

        if not got_adb:
            raise unittest.SkipTest("adb not found")

        cls.devices = []
        process = subprocess.Popen(['adb', 'devices'], stdout=subprocess.PIPE)
        process.stdout.readline()  # Skip the first line
        for line in process.stdout:
            line = line.strip()
            if line:
                try:
                    adb_id, dev_state = line.split()
                except ValueError:
                    continue

                if dev_state == 'device':
                    cls.devices.append(adb_id)

        if len(cls.devices) == 0:
            raise unittest.SkipTest(
                "no android devices found, cannot test adb"
            )
        if len(cls.devices) > 1:
            raise unittest.SkipTest(
                "more than 1 android device found, cannot run tests"
            )
        # backup any existing config
        # set root backup dir
        super(AdbTest, cls).setUpClass()
        cls.android_root = '/sdcard/tmp/backpy'

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(AdbTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(AdbTest, self).setUp()
        # clear dest folder
        backpy.delete_temp_files(self.dest_root)
        # copy source files onto device
        self.push_files(
            os.path.join(self.project_dir, 'resources', 'source_files'),
            '{0}/source_files'.format(self.android_root)
        )

        self.one_folder = os.path.join(self.dest_root, 'one')
        self.six_seven_folder = os.path.join(self.dest_root, 'six seven')

    def tearDown(self):
        self.delete_files(self.android_root)

    def push_files(self, src, dest):
        try:
            with open(os.devnull, 'w') as fp:
                subprocess.call(['adb', 'push', src, dest], stdout=fp)
        except subprocess.CalledProcessError:
            backpy.logger.warning('could not copy files to phone')

    def delete_files(self, path):
        try:
            with open(os.devnull, 'w') as fp:
                subprocess.call(['adb', 'shell', 'rm', '-rf', path], stdout=fp)
        except subprocess.CalledProcessError:
            backpy.logger.warning('could not delete source files from phone')

    def create_file(self, filepath, text):
        with open(os.path.join(self.src_root, filepath), 'a') as f:
            f.write(text)
        self.push_files(os.path.join(self.src_root, filepath), '{0}/source_files/{1}'.format(self.android_root, filepath.replace(os.sep, '/')))

    def change_one_four_five(self, text):
        super(AdbTest, self).change_one_four_five(text)
        self.push_files(
            os.path.join(self.src_root, 'one', 'four', 'five'),
            '{0}/source_files/one/four/five'.format(self.android_root)
        )

    def testInitialBackup(self):
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)

    def testSecondBackup(self):
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        self.change_one_four_five('some more text')
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)

    def testDeleteFileAndBackup(self):
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        self.change_one_four_five('some more text')
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        self.change_one_four_five('yet more text')
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)

        # delete file
        self.delete_files('{0}/source_files/one/four/five'.format(self.android_root))

        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 4)

    def testAddNewFileAndBackup(self):
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        backpy.perform_backup(['{0}/source_files/six seven'.format(self.android_root), self.six_seven_folder], self.mock_timestamp(), True)

        self.create_file(os.path.join('six seven', 'eleven'), 'new file\n')

        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        backpy.perform_backup(['{0}/source_files/six seven'.format(self.android_root), self.six_seven_folder], self.mock_timestamp(), True)

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 1)
        self.assertEqual(zips_in_six_seven, 2)

    def testDeleteFolderAndBackup(self):
        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        backpy.perform_backup(['{0}/source_files/six seven'.format(self.android_root), self.six_seven_folder], self.mock_timestamp(), True)

        # create a new folder and file
        os.mkdir(os.path.join(self.src_root, 'six seven', 'twelve'))
        self.create_file(os.path.join('six seven', 'twelve', 'eleven'), 'new file\n')

        # delete a folder
        self.delete_files('{0}/source_files/one/four'.format(self.android_root))

        backpy.perform_backup(['{0}/source_files/one'.format(self.android_root), self.one_folder], self.mock_timestamp(), True)
        backpy.perform_backup(['{0}/source_files/six seven'.format(self.android_root), self.six_seven_folder], self.mock_timestamp(), True)

        # count zips
        zips_in_one = self.count_files(os.path.join(self.one_folder, '*.tar.gz'))
        zips_in_six_seven = self.count_files(os.path.join(self.six_seven_folder, '*.tar.gz'))
        self.assertEqual(zips_in_one, 2)
        self.assertEqual(zips_in_six_seven, 2)

    # TODO restore tests

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(AdbTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
