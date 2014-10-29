#!/usr/bin/env python

import os
from setuptools import setup

for line in open(os.path.join('backpy', 'backpy.py')):
    if '__version__ = ' in line:
        version = eval(line.split('=')[-1])
        break
else:
    raise AssertionError('__version__ = "VERSION" must be in backpy.py')

setup(
    name='backpy',
    version=version,
    description='Python backup utility',
    packages=['backpy'],
    include_package_data=True,
    install_requires=['python-dateutil', 'argparse'],
    test_suite='backpy_tests',
    zip_safe=False,
)
