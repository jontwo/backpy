#!/usr/bin/python2

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

__author__ = 'Steffen Schneider'
__version__ = '1.0'
__copyright__ = 'Simplified BSD license'

import os
import re
import tarfile
from argparse import ArgumentParser
from datetime import datetime
from hashlib import md5


class FileIndex:
    def __init__(self, path, exclusion_rules=None):
        if exclusion_rules is None:
            exclusion_rules = []
        self.__files__ = dict()
        self.__dirs__ = []
        self.__path__ = path
        self.__exclusion_rules__ = exclusion_rules
        pass

    def is_valid(self, filename):
        if self.__exclusion_rules__ is not None:
            for regex in self.__exclusion_rules__:
                if re.match(regex, filename) is not None:
                    return False
        return True

    # TODO get skip to work
    def gen_index(self):
        for dirname, dirnames, filenames in os.walk(self.__path__):
            if not self.is_valid(dirname):
                print 'skip directory: %s (exclusion)' % dirname
                continue
            for subdirname in dirnames:
                fullpath = os.path.join(dirname, subdirname)
                if self.is_valid(fullpath):
                    self.__dirs__.append(fullpath)
                else:
                    print 'skip directory: %s (exclusion)' % fullpath
            for filename in filenames:
                fullname = os.path.join(dirname, filename)
                if not self.is_valid(fullname):
                    print 'skipping file: %s (exclusion)' % fullname
                    continue
                try:
                    f = open(fullname)
                    md5hash = md5(f.read())
                    f.close()
                    self.__files__[fullname] = ''.join(
                        ['%x' % ord(h) for h in md5hash.digest()]
                    )
                except IOError:
                    print 'skipping file: %s' % fullname

    def files(self):
        return self.__files__.keys()

    def hash(self, f):
        return self.__files__[f] if f in self.__files__ else None

    def write_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        index = open(path, 'w+')
        index.writelines(["%s\n" % s for s in self.__dirs__])
        index.write('# files\n')
        index.writelines(
            ['%s@@@%s\n' % (f, self.hash(f)) for f in self.files()]
        )
        index.flush()
        index.close()

    def read_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        index = open(path)
        line = index.readline()
        # read all directories
        while line != '# files\n':
            self.__dirs__.append(line[:len(line) - 1])
            line = index.readline()
            # read all files
        for line in index.readlines():
            [fname, _hash] = line[:len(line) - 1].split('@@@')
            self.__files__[fname] = _hash
        index.close()

    def get_diff(self, index=None):
        filelist = []
        for f in self.files():
            if index is None or self.hash(f) != index.hash(f):
                filelist.append(f)
        return filelist


class Backup:
    def __init__(
        self, path, index, parent=None,
        timestamp=datetime.now().strftime('%Y%m%d%H%M%S')
    ):
        self.__path__ = path
        self.__timestamp__ = timestamp
        self.__old_index__ = parent.__new_index__ \
            if parent is not None else None
        self.__new_index__ = index

    def get_tarpath(self):
        return os.path.join(self.__path__,
                            '%s_backup.tar.gz' % self.__timestamp__)

    def write_to_disk(self):
        tar = tarfile.open(self.get_tarpath(), 'w:gz')
        # write index
        path = './.%s_index' % self.__timestamp__
        self.__new_index__.write_index(path)
        tar.add(path, '.index')
        print 'deleting %s...' % path
        del path
        # write files
        for f in self.__new_index__.get_diff(self.__old_index__):
            print 'adding %s...' % f
            tar.add(f)
        tar.close()

    def full_recovery(self):
        tar = tarfile.open(os.path.join(
            self.__path__,
            'full/%s_fullbackup.tar.gz' % datetime.now().strftime(
                '%Y%m%d%H%M%S'
            )), 'w:gz')
        backups = all_backups(self.__path__)
        i = 0
        new_queue = []
        queue = self.__new_index__.files()
        while queue and i < len(backups):
            current_backup = read_backup(
                os.path.join(self.__path__, backups[i])
            )
            current_tar = tarfile.open(current_backup.get_tarpath(), 'r:*')
            i += 1
            while queue:
                filename = queue.pop()
                if filename[0] == '/':
                    filename = filename[1:]
                try:
                    member = current_tar.getmember(filename)
                    tar.addfile(member)
                except KeyError:
                    new_queue.append(filename)
            current_tar.close()
            queue = new_queue
            new_queue = []
        tar.close()
        return len(queue)


def read_backup(path):
    timestamp = os.path.basename(path).split('_')[0]
    print 'time %s path %s' % (timestamp, path)
    tar = tarfile.open(path, 'r:*')
    temp_path = './.%sindex' % timestamp
    tar.extract('.index', temp_path)
    index = FileIndex(temp_path)
    index.read_index(os.path.join(temp_path, '.index'))
    return Backup(os.path.dirname(path), index, None, timestamp)


def all_backups(path):
    if os.path.isabs(path) is None:
        path = os.path.join(os.path.curdir, path)
    if not os.path.exists(path):
        os.makedirs(path)
    files = os.listdir(path)
    backups = []
    for f in files:
        if os.path.basename(f).endswith('.tar.gz'):
            backups.append(f)
    backups.sort(reverse=True)
    return backups


def latest_backup(path):
    backups = all_backups(path)
    return read_backup(os.path.join(path, backups[0])) \
        if len(backups) > 0 else None


def read_directory_list(path):
    l = open(path)
    dirs = []
    for line in l:
        dirs.append(line[:-1].split(','))
    l.close()
    return dirs


def write_directory_list(path, dirlist):
    l = open(path, "w+")
    for pair in dirlist:
        s = '%s,%s\n' % (pair[0], pair[1])
        print 'add entry %s in directory list' % s[:-1]
        l.write(s)
    l.flush()
    l.close()


def show_directory_list(dirs):
    print 'Backup directories:'
    for line in dirs:
        if len(line) < 2:
            print 'Bad config entry:'
            print line
            return
        print 'From %s to %s' % (line[0], line[1])
        skips = ', '.join(line[2:])
        if skips:
            print '  skipping %s' % skips


def add_directory(path, src, dest):
    l = open(path, 'a+')
    new_line = '%s,%s\n' % (src, dest)
    if not new_line.lower() in (line.lower() for line in l):
        l.write(new_line)
        l.flush()
        l.close()


def full_backup(path):
    backup = latest_backup(path)
    files_left = backup.full_recovery()
    if files_left > 0:
        print 'error: not all files could be recovered\n%d files left' \
              % files_left
    else:
        print 'backup successful'


def perform_backup(src, dest, skip=None):
    print 'backup of directory %s to %s' % (src, dest)
    if skip is not None:
        print 'skipping files/directories that match %s' % ' or '.join(skip)
    f = FileIndex(src, skip)
    f.gen_index()
    backup = Backup(dest, f, latest_backup(dest))
    backup.write_to_disk()
    # TODO delete indexes


def init(file_config):
    try:
        f = open(file_config)
        f.close()
    except IOError:
        print 'init backup directory list'
        f = open(file_config, 'w+')
        f.close()


def parse_args():
    parser = ArgumentParser(description='Command line backup utility')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list', dest='list', action='store_true',
                       required=False, help='list the all the directories \
                       currently in the config file.')
    group.add_argument('-a', '--add', metavar='path', nargs=2,
                       dest='add_path', required=False,
                       help='adds the specified source directory to the\
                       backup index. The backups will be stored in the\
                       specified destination directory.')
    group.add_argument('-s', '--skip', dest='skip', metavar='regex', nargs='+',
                       required=False,
                       help='skips all files/directories that match the given\
                       regular expression')
    group.add_argument('-d', '--delete', metavar='path', nargs=2,
                       dest='delete_path', required=False,
                       help='remove the specified source and destination\
                       directories from the backup.lst file.')
    group.add_argument('-b', '--backup', action='store_true', dest='backup',
                       help='performs a backup for all path specified in the\
                       backup.lst file')
    group.add_argument('-r', '--restore', action='store_true', dest='restore',
                       help='restore selected files **NOT IMPLEMENTED**')
    return vars(parser.parse_args())

if __name__ == '__main__':
    config_file = os.path.expanduser('~/.backpy')
    init(config_file)
    backup_dirs = read_directory_list(config_file)
    args = parse_args()
    if args['skip']:
        for arg in args['skip']:
            print 'skipping %s' % arg
    elif args['backup']:
        print 'backing up'
        # for directory in backup_dirs:
        #     print 'backup of %s' % directory
        #     perform_backup(directory[0], directory[1], args['skip'])
    elif args['restore']:
        print 'restore is not implemented'
    elif args['add_path']:
        add_directory(
            config_file, args['add_path'][0], args['add_path'][1]
        )
    elif args['delete_path']:
        print 'removing path'
    elif args['list']:
        show_directory_list(backup_dirs)
    else:
        print "Please specify a program option.\n" + \
              "Invoke with --help for futher information."
