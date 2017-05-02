#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import backup
import common
import os
import platform
import re
import restore
import subprocess
import time
import unittest


def log_subprocess_output(pipe):
    if not pipe:
        return

    for line in map(str.strip, pipe.split('\n')):
        if line:
            backpy.logger.debug('ADB: {0}'.format(line))


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
        cls.android_root = '/sdcard/tmp/backpy/source_files'

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
            self.android_root
        )

        self.one_folder = os.path.join(self.dest_root, 'one')
        self.six_seven_folder = os.path.join(self.dest_root, 'six seven')
        self.files_to_backup = [
            ['{0}/one'.format(self.android_root), self.one_folder],
            ['{0}/six seven'.format(self.android_root), self.six_seven_folder]
        ]
        backpy.logger.debug('AdbTest setUp done')

    def tearDown(self):
        super(AdbTest, self).tearDown()
        self.delete_files(self.android_root)

    def call_adb(self, cmd, err_msg='adb error', check_output=False):
        # call adb command and suppress output
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output, error = process.communicate()
            log_subprocess_output(error)
            if check_output:
                return output
            else:
                log_subprocess_output(output)
        except subprocess.CalledProcessError:
            backpy.logger.warning(err_msg)

    def get_android_path(self, pc_path):
        return pc_path.replace(self.src_root, self.android_root).replace(os.sep, '/')

    def push_files(self, src, dest):
        backpy.logger.warning('pushing {0} to {1}'.format(src, dest))
        self.call_adb(['adb', 'push', src, dest], 'could not copy files to phone')

    def delete_files(self, path):
        self.call_adb(['adb', 'shell', 'rm', '-rf', path], 'could not delete source files from phone')

    def create_file(self, filepath, text):
        # create file on PC then copy to phone
        backpy.logger.debug('adb create file {0}'.format(filepath))
        super(AdbTest, self).create_file(filepath, text)
        android_filepath = self.get_android_path(filepath)
        self.push_files(filepath, android_filepath)

    def create_folder(self, folderpath):
        # create folder both on PC and on phone
        backpy.logger.debug('adb create folder {0}'.format(folderpath))
        super(AdbTest, self).create_folder(folderpath)
        android_folderpath = self.get_android_path(folderpath)
        self.call_adb(['adb', 'shell', 'mkdir', android_folderpath], 'could not create folder on phone')

    def text_in_file(self, filename, text):
        android_filename = self.get_android_path(filename)
        file_contents = subprocess.check_output(['adb', 'shell', 'cat', android_filename])
        return text in file_contents

    def get_last_line(self, filename):
        android_filename = self.get_android_path(filename)
        lines = subprocess.check_output(
            ['adb', 'shell', 'cat', android_filename]
        ).strip().split('\n')
        return lines[-1] if lines else ''

    def do_backup(self):
        for f in self.files_to_backup:
            backpy.perform_backup(f, self.mock_timestamp(), True)

    def do_restore(self, files=None, chosen_index=None):
        backpy.perform_restore(self.files_to_backup, files, chosen_index)

    def list_files(self, folder):
        files = subprocess.check_output(
            ['adb', 'shell', 'ls', folder]
        ).split('\n')
        return map(str.strip, files)

    def get_files_in_src(self):
        return self.list_files(self.android_root)

    def get_files_in_one(self):
        return self.list_files('{0}/one'.format(self.android_root))

    def get_files_in_four(self):
        return self.list_files('{0}/one/four'.format(self.android_root))

    def get_one_four_five_path(self):
        return '{0}/one/four/five'.format(self.android_root)

    def get_six_seven_path(self):
        return '{0}/six seven'.format(self.android_root)

    def change_one_four_five(self, text):
        super(AdbTest, self).change_one_four_five(text)
        self.push_files(
            os.path.join(self.src_root, 'one', 'four', 'five'),
            '{0}/one/four/five'.format(self.android_root)
        )

    def delete_one_four(self):
        self.delete_files('{0}/one/four'.format(self.android_root))

    def delete_one_four_five(self):
        self.delete_files('{0}/one/four/five'.format(self.android_root))

    def delete_one_nine_ten(self):
        self.delete_files('{0}/one/nine ten'.format(self.android_root))

    def delete_six_seven(self):
        self.delete_files('{0}/six seven'.format(self.android_root))

    def delete_all_folders(self):
        self.delete_files(self.android_root)

    def get_file_timestamp(self, filename):
        android_filename = self.get_android_path(filename)
        str_time = self.call_adb(
            ['adb', 'shell', 'ls', '-al', android_filename],
            'could not get timestamp', True
        )
        m = re.search('(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', str_time)
        if m and m.groups():
            time_time = time.strptime(m.group(1), '%Y-%m-%d %H:%M')
            return time.mktime(time_time)
        return 0

    def change_file_timestamp(self, filename):
        super(AdbTest, self).change_file_timestamp(filename)
        file_dest = self.get_android_path(filename)
        self.push_files(filename, file_dest)


class AdbBackupTest(AdbTest, backup.BackupTest):
    @classmethod
    def setUpClass(cls):
        # backup any existing config
        # set root backup dir
        super(AdbBackupTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(AdbBackupTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(AdbBackupTest, self).setUp()

    @unittest.skip('not applicable')
    def testAddSkipAndBackup(self):
        pass

    @unittest.skip('not applicable')
    def testAddSkipWithWildcard(self):
        pass


class AdbRestoreTest(AdbTest, restore.RestoreTest):
    @classmethod
    def setUpClass(cls):
        # backup any existing config
        # set root backup dir
        super(AdbRestoreTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(AdbRestoreTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(AdbRestoreTest, self).setUp()

    @unittest.skip('not applicable')
    # does not apply to adb as hashes are partly based on timestamp
    # if timestamp changes, hash will change, so file will be restored
    # unlike pc, where changing timestamp will not cause file to be
    # backed up/restored
    def testRestoreOneFileUnchanged(self):
        pass

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(AdbBackupTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
    suite = unittest.TestLoader().loadTestsFromTestCase(AdbRestoreTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
