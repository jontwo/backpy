"""Tests for adb backup mode."""

import logging
import os
import re
import subprocess
import time
import unittest

import pytest

from backpy.backpy import perform_backup, perform_restore
from backpy.helpers import delete_temp_files, is_windows
from backpy.logger import LOG_NAME
from . import backup_test, common, restore_test

LOG = logging.getLogger(LOG_NAME)


def log_subprocess_output(pipe):
    if not pipe:
        return

    for line in map(str.strip, pipe.split("\n")):
        if line:
            LOG.debug("ADB: %s", line)


def call_adb(cmd, err_msg="adb error", check_output=False):
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
        LOG.warning(err_msg)


def push_files(src, dest):
    LOG.warning("pushing %s to %s", src, dest)
    call_adb(["adb", "push", src, dest], "could not copy files to phone")


def list_files(folder):
    files = subprocess.check_output(["adb", "shell", "ls", folder]).decode("latin1").split("\n")
    return [f.strip() for f in files]


class AdbTest(common.BackpyTest):
    devices = None

    @classmethod
    def setUpClass(cls):
        # check adb is installed and one device is connected
        adb_exe = "adb.exe" if is_windows() else "adb"
        got_adb = False
        for folder in os.getenv("PATH").split(os.pathsep):
            if os.path.exists(os.path.join(folder, adb_exe)):
                got_adb = True
                break

        if not got_adb:
            raise unittest.SkipTest("adb not found")

        cls.devices = []
        process = subprocess.Popen(["adb", "devices"], stdout=subprocess.PIPE)
        process.stdout.readline()  # Skip the first line
        for line in process.stdout:
            line = line.strip()
            if line:
                try:
                    adb_id, dev_state = line.split()
                except ValueError:
                    continue

                if dev_state == "device":
                    cls.devices.append(adb_id)

        if len(cls.devices) == 0:
            raise unittest.SkipTest("no android devices found, cannot test adb")
        if len(cls.devices) > 1:
            raise unittest.SkipTest("more than 1 android device found, cannot run tests")
        # backup any existing config
        # set root backup dir
        super(AdbTest, cls).setUpClass()
        cls.android_root = "/sdcard/tmp/backpy/source_files"

    @classmethod
    def tearDownClass(cls):
        # keep config for reference
        # restore original config
        super(AdbTest, cls).tearDownClass()

    def setUp(self):
        # start test with blank config
        super(AdbTest, self).setUp()
        # clear dest folder
        delete_temp_files(self.dest_root)
        # copy source files onto device
        push_files(os.path.join(self.project_dir, "resources", "source_files"), self.android_root)

        self.one_folder = os.path.join(self.dest_root, "one")
        self.six_seven_folder = os.path.join(self.dest_root, "six seven")
        self.files_to_backup = [
            ["{0}/one".format(self.android_root), self.one_folder],
            ["{0}/six seven".format(self.android_root), self.six_seven_folder],
        ]
        LOG.debug("AdbTest setUp done")

    def tearDown(self):
        super(AdbTest, self).tearDown()
        self.delete_files(self.android_root)

    def get_android_path(self, pc_path):
        return pc_path.replace(self.src_root, self.android_root).replace(os.sep, "/")

    def delete_files(self, path):
        call_adb(["adb", "shell", "rm", "-rf", path], "could not delete source files from phone")

    def create_file(self, filepath, text):
        # create file on PC then copy to phone
        LOG.debug("adb create file %s", filepath)
        super(AdbTest, self).create_file(filepath, text)
        android_filepath = self.get_android_path(filepath)
        push_files(filepath, android_filepath)

    def create_folder(self, folderpath):
        # create folder both on PC and on phone
        LOG.debug("adb create folder %s", folderpath)
        super(AdbTest, self).create_folder(folderpath)
        android_folderpath = self.get_android_path(folderpath)
        call_adb(["adb", "shell", "mkdir", android_folderpath], "could not create folder on phone")

    def text_in_file(self, filename, text):
        android_filename = self.get_android_path(filename)
        file_contents = subprocess.check_output(["adb", "shell", "cat", android_filename])
        return text in file_contents

    def get_last_line(self, filename):
        android_filename = self.get_android_path(filename)
        lines = (
            subprocess.check_output(["adb", "shell", "cat", android_filename])
            .decode("latin1")
            .strip()
            .split("\n")
        )
        return lines[-1] if lines else ""

    def do_backup(self):
        for f in self.files_to_backup:
            perform_backup(f, self.mock_timestamp(), True)

    def do_restore(self, files=None, chosen_index=None):
        perform_restore(self.files_to_backup, files, chosen_index)

    def get_files_in_src(self):
        return list_files(self.android_root)

    def get_files_in_one(self):
        return list_files("{0}/one".format(self.android_root))

    def get_files_in_four(self):
        return list_files("{0}/one/four".format(self.android_root))

    def get_one_four_five_path(self):
        return "{0}/one/four/five".format(self.android_root)

    def get_six_seven_path(self):
        return "{0}/six seven".format(self.android_root)

    def change_one_four_five(self, text):
        super(AdbTest, self).change_one_four_five(text)
        push_files(
            os.path.join(self.src_root, "one", "four", "five"),
            "{0}/one/four/five".format(self.android_root),
        )

    def delete_one_four(self):
        self.delete_files("{0}/one/four".format(self.android_root))

    def delete_one_four_five(self):
        self.delete_files("{0}/one/four/five".format(self.android_root))

    def delete_one_nine_ten(self):
        self.delete_files("{0}/one/nine ten".format(self.android_root))

    def delete_six_seven(self):
        self.delete_files("{0}/six seven".format(self.android_root))

    def delete_all_folders(self):
        self.delete_files(self.android_root)

    def get_file_timestamp(self, filename):
        android_filename = self.get_android_path(filename)
        str_time = call_adb(
            ["adb", "shell", "ls", "-al", android_filename], "could not get timestamp", True
        ).decode("latin1")
        m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", str_time)
        if m and m.groups():
            time_time = time.strptime(m.group(1), "%Y-%m-%d %H:%M")
            return time.mktime(time_time)
        return 0

    def change_file_timestamp(self, filename):
        super(AdbTest, self).change_file_timestamp(filename)
        file_dest = self.get_android_path(filename)
        push_files(filename, file_dest)


class AdbBackupTest(AdbTest, backup_test.BackupTest):
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

    @pytest.mark.skip("not applicable")
    def test_add_skip_and_backup(self):
        pass

    @pytest.mark.skip("not applicable")
    def test_add_skip_with_wildcard(self):
        pass


class AdbRestoreTest(AdbTest, restore_test.RestoreTest):
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

    @pytest.mark.skip("not applicable")
    # does not apply to adb as hashes are partly based on timestamp
    # if timestamp changes, hash will change, so file will be restored
    # unlike pc, where changing timestamp will not cause file to be
    # backed up/restored
    def test_restore_one_file_unchanged(self):
        pass
