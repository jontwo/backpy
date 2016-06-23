#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backpy
import os
import platform
import subprocess
import unittest


class AdbTest(unittest.TestCase):
    src_dir = '/sdcard/tmp/backpy'
    root_dir = '.'

    @classmethod
    def setUpClass(cls):
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

        # TODO setup push resources files onto device
        # TODO teardown delete src dir

    def testPass(self):
        self.assertEqual(1, 1)

    # TODO add tests
    # initial backup
    # add file
    # remove file
    # add folder
    # remove folder
    # update file

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(AdbTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
