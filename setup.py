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
    install_requires=['argparse'],
    test_suite='backpy_tests',
    zip_safe=False,
    author='Steffen Schneider',
    author_email='stes@users.noreply.github.com',
    maintainer='Jon Morris',
    maintainer_email='jontwo@users.noreply.github.com',
    url='https://github.com/jontwo/backpy',
    entry_points={
        'console_scripts': [
            'backpy = backpy.backpy:run_backpy'
        ]
    },
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Archiving :: Backup',
    ]
)
