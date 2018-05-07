#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Steffen Schneider <stes94@ymail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer. Redistributions in binary
form must reproduce the above copyright notice, this list of conditions and
the following disclaimer in the documentation and/or other materials provided
with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

"""
# StdLib imports
import fnmatch
import os
import re
import subprocess

# Project imports
from helpers import (
    CONFIG_FILE,
    SKIP_KEY,
    list_contains,
    get_file_hash,
    get_filename_index,
    get_folder_index,
    get_config_key,
    is_windows,
    read_config_file
)
from logger import logger

ANDROID_SKIPS = os.path.join(os.path.expanduser('~'), '.androidSkipFolders')


class FileIndex:
    def __init__(self, path, exclusion_rules=None, reading=False, adb=False):
        if exclusion_rules is None:
            exclusion_rules = []
        self.__files__ = dict()
        self.__dirs__ = [path]
        self.__path__ = path
        self.__exclusion_rules__ = exclusion_rules or []
        self.__adb__ = adb
        # add global skips to exclusion rules
        global_skips = get_config_key(CONFIG_FILE, SKIP_KEY)
        if global_skips:
            self.__exclusion_rules__.extend(global_skips[0].split(','))
            logger.debug('init exclusion rules = %s', self.__exclusion_rules__)
        if adb:
            logger.debug('new FileIndex for {0}, adb=True'.format(path))
        # suppress warning when reading an existing index
        if not reading and not self.is_valid(path):
            logger.warning('root dir %s does not exist or is excluded' % path)

    def is_valid(self, f):
        if self.__adb__:
            if re.match('.*/cache', f):
                return False
            if os.path.exists(ANDROID_SKIPS):
                with open(ANDROID_SKIPS) as skip_list:
                    for entry in skip_list:
                        if f.startswith(entry.strip()):
                            logger.debug('SKIPPING %s' % f)
                            return False
        elif not os.path.exists(f):
            return False
        if self.__exclusion_rules__:
            for regex in self.__exclusion_rules__:
                if is_windows():
                    if fnmatch.fnmatch(f, regex):
                        return False
                else:
                    if fnmatch.fnmatchcase(f, regex):
                        return False
        return True

    def gen_index(self):
        if self.__adb__:
            logger.info('generating index of android device')
            self.adb_read_folder(self.__path__)
            return

        logger.info('generating index of {0}'.format(self.__path__))
        for dirname, dirnames, filenames in os.walk(self.__path__):
            if not self.is_valid(dirname):
                continue
            for subdirname in dirnames:
                fullpath = os.path.join(dirname, subdirname)
                if self.is_valid(fullpath):
                    self.__dirs__.append(fullpath)
                else:
                    dirnames.remove(subdirname)
                    logger.debug('skipping directory: %s' % fullpath)
            for filename in filenames:
                fullname = os.path.join(dirname, filename)
                if not self.is_valid(fullname):
                    logger.debug('skipping file: %s' % fullname)
                    continue
                digest = get_file_hash(fullname)
                if digest:
                    self.__files__[fullname] = digest

    def files(self):
        return self.__files__.keys()

    def dirs(self):
        return self.__dirs__

    def skips(self):
        return self.__exclusion_rules__

    def hash(self, f, exact_match=True):
        if exact_match:
            return self.__files__[f] if f in self.__files__ else None
        else:
            index = get_filename_index(f, self.__files__)
            return None if index is None else self.hash(self.files()[index])

    def is_folder(self, f, exact_match=True):
        if exact_match:
            return list_contains(f, self.__dirs__)
        else:
            return get_folder_index(f, self.__dirs__) is not None

    def write_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        logger.debug('writing index to %s' % path)
        with open(path, 'w+') as index:
            # BREAKING CHANGE: if you read this index with an old version
            # of backpy, you'll get a [adb=x] folder
            index.write('[adb={0}]\n'.format(self.__adb__))
            index.writelines(["%s\n" % s for s in self.__dirs__])
            index.write('# files\n')
            index.writelines(['%s@@@%s\n' % (f, self.hash(f)) for f in self.files()])

    def read_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        logger.debug('reading index at %s' % path)
        if not os.path.exists(path):
            logger.debug('not found, returning')
            return
        index = read_config_file(path)
        logger.debug('READ INDEX %s', index)
        for k, v in index.iteritems():
            if k == 'adb':
                self.__adb__ = v == 'True'
            elif k == 'files':
                for f in v:
                    [fname, _hash] = f.split('@@@')
                    self.__files__[fname] = _hash
            elif k == 'dirs':
                self.__dirs__.extend([d for d in v if d not in self.dirs()])
            elif k == 'default':
                # items without a header, i.e. pre-1.5.0 style index
                in_files = False
                for line in v:
                    if line == '# files':
                        in_files = True
                        continue
                    if in_files:
                        # add file
                        [fname, _hash] = line.split('@@@')
                        self.__files__[fname] = _hash
                    elif line not in self.dirs():
                        # add directory
                        self.__dirs__.append(line)

    def get_diff(self, index=None):
        filelist = []
        for f in self.files():
            if index is None or self.hash(f) != index.hash(f):
                filelist.append(f)
        return filelist

    def get_missing(self, index=None):
        if not index:
            return []
        return filter(lambda x: x not in self.files(), index.files())

    def adb_read_folder(self, path):
        """
        Use adb to list all files and folders in path, hashing with full file path,
        modified date and time, and size
        :param path: full path of the folder to read
        """
        logger.debug('reading adb folder %s' % path)
        # check files in this folder
        for out in subprocess.check_output(['adb', 'shell', 'ls', '-l',
                                            re.escape(path)]).split('\n'):
            file_info = out.strip()
            if not len(file_info):
                continue
            line = file_info.split()
            f_size = None
            try:
                f_permissions = line.pop(0)
                if f_permissions == 'total':
                    continue
                # 2nd item may or may not be links, try converting to int
                f_owner = line.pop(0)
                try:
                    f_links = int(f_owner)
                    f_owner = line.pop(0)
                except ValueError:
                    pass
                f_group = line.pop(0)
                f_size = line.pop(0)
                f_date = line.pop(0)
                f_time = line.pop(0)
                f_name = ' '.join(line)
            except IndexError:
                logger.warning('could not extract info from %s' % file_info)
                continue

            # check for slash before adding sub path
            if path[-1] == '/':
                fullname = '%s%s' % (path, f_name)
            else:
                fullname = '%s/%s' % (path, f_name)

            if self.is_valid(fullname):
                if f_permissions.startswith('d'):
                    # folder - add to list and search subfolders
                    self.__dirs__.append(fullname)
                    self.adb_read_folder(fullname)
                else:
                    # file - hash and add to list
                    digest = get_file_hash(fullname, f_date + f_time, f_size)
                    if digest:
                        self.__files__[fullname] = digest
