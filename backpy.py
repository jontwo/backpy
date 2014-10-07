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

__author__ = 'Steffen Schneider'
__version__ = '1.0'
__copyright__ = 'Simplified BSD license'

import logging
import logging.handlers
import os
import re
import sys
import tarfile
from argparse import ArgumentParser
from datetime import datetime
from hashlib import md5
from pdb import set_trace


class SpecialFormatter(logging.Formatter):
    FORMATS = {logging.DEBUG: "DEBUG: %(lineno)d: %(message)s",
               logging.INFO: "%(message)s",
               'DEFAULT': "%(levelname)s: %(message)s"}

    def format(self, record):
        self._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        return logging.Formatter.format(self, record)


class FileIndex:
    def __init__(self, path, exclusion_rules=None, reading=False):
        if exclusion_rules is None:
            exclusion_rules = []
        self.__files__ = dict()
        self.__dirs__ = []
        self.__path__ = path
        self.__exclusion_rules__ = exclusion_rules
        # suppress warning when reading an existing index
        if not reading and not self.is_valid(path):
            logger.warning('root dir %s does not exist or is excluded' % path)

    def is_valid(self, filename):
        if not os.path.exists(filename):
            return False
        if self.__exclusion_rules__:
            for regex in self.__exclusion_rules__:
                if re.match(regex, filename) is not None:
                    return False
        return True

    def gen_index(self):
        logger.debug('generating index')
        for dirname, dirnames, filenames in os.walk(self.__path__):
            if not self.is_valid(dirname):
                continue
            for subdirname in dirnames:
                fullpath = os.path.join(dirname, subdirname)
                if self.is_valid(fullpath):
                    self.__dirs__.append(fullpath)
                else:
                    logger.info('skipping directory: %s' % fullpath)
            for filename in filenames:
                fullname = os.path.join(dirname, filename)
                # if not self.is_valid(fullname):
                #     logger.info('skipping file: %s' % fullname)
                #     continue
                try:
                    f = open(fullname)
                    md5hash = md5(f.read())
                    f.close()
                    self.__files__[fullname] = ''.join(
                        ['%x' % ord(h) for h in md5hash.digest()]
                    )
                except IOError:
                    logger.warning('could not process file: %s' % fullname)

    def files(self):
        return self.__files__.keys()

    def hash(self, f, exact_match=True):
        if exact_match:
            return self.__files__[f] if f in self.__files__ else None
        else:
            index = get_filename_index(f, self.__files__)
            return self.hash(self.files()[index]) if index else None

    def is_folder(self, f):
        return list_contains(f, self.__dirs__)

    def write_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        logger.debug('writing index to %s' % path)
        with open(path, 'w+') as index:
            index.writelines(["%s\n" % s for s in self.__dirs__])
            index.write('# files\n')
            index.writelines(
                ['%s@@@%s\n' % (f, self.hash(f)) for f in self.files()]
            )

    def read_index(self, path=None):
        if path is None:
            path = os.path.join(self.__path__, '.index')
        logger.debug('reading index at %s' % path)
        if not os.path.exists(path):
            logger.debug('not found, returning')
            return
        with open(path) as index:
            line = index.readline()
            # read all directories
            while line != '# files\n':
                self.__dirs__.append(line[:len(line) - 1])
                line = index.readline()
                # read all files
            for line in index.readlines():
                [fname, _hash] = line[:len(line) - 1].split('@@@')
                self.__files__[fname] = _hash

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
        if not len(self.__new_index__.files()):
            logger.warning('no files to back up')
            return

        logger.debug('writing files to backup')
        with tarfile.open(self.get_tarpath(), 'w:gz') as tar:
            # write index
            path = os.path.join('.', '.%s_index' % self.__timestamp__)
            self.__new_index__.write_index(path)
            tar.add(path, '.index')
            # delete temp index now we've written it
            delete_temp_files(path)
            # write files
            for f in self.__new_index__.get_diff(self.__old_index__):
                logger.info('adding %s...' % f)
                tar.add(f)
                # TODO do not keep index if nothing added?

    # TODO platform independent paths
    # TODO recovery of single file (search all backups for most recent)
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

    def contains_file(self, file, exact_match=True):
        """look for a specific file in the index, return the hash
        if found or None if not"""
        logger.debug('find file %s' % file)
        return self.__new_index__.hash(file, exact_match)

    def contains_folder(self, folder):
        """look for a specific folder in the index"""
        logger.debug('find folder %s' % folder)
        return self.__new_index__.is_folder(folder)

    def restore_folder(self, folder):
        logger.debug('restoring folder %s' % folder)

        # get destination dir
        # index destination dir
        # diff then restore changed files

        # dest = None
        # for dirs in dirlist:
        #     if string_equals(dirs[1], os.path.dirname(zip_path)):
        #         dest = dirs[0]
        # if dest:
        #     logger.info('restoring %s from %s to %s' % (folder, zip_path, dest))

    def restore_file(self, file):
        logger.debug('restoring file %s' % file)
        # get destination dir
        # index destination dir
        # diff then restore if file changed


def delete_temp_files(path):
    """Attempt to delete temporary files or folders in the given path.
    Just carry on if any can't be deleted."""
    if os.path.isfile(path):
        # single file - delete it and return
        try:
            os.unlink(path)
        except WindowsError:
            logger.warning('could not delete %s' % path)
        return

    if os.path.isdir(path):
        # directory - delete subfiles and folders then delete it
        for f in os.listdir(path):
            delete_temp_files(os.path.join(path, f))
        try:
            os.rmdir(path)
        except WindowsError:
            logger.warning('could not delete %s' % path)


def read_backup(path):
    logger.debug('reading backup %s' % path)
    timestamp = os.path.basename(path).split('_')[0]
    temp_path = os.path.join('.', '.%sindex' % timestamp)
    try:
        with tarfile.open(path, 'r:*') as tar:
            tar.extract('.index', temp_path)
    except tarfile.ReadError as e:
        logger.error(e.message)
    finally:
        index = FileIndex(temp_path, reading=True)
        index.read_index(os.path.join(temp_path, '.index'))
        # delete temp index now we've read it
        delete_temp_files(temp_path)
        return Backup(os.path.dirname(path), index, None, timestamp)


def all_backups(path):
    logger.debug('finding previous backups')
    backups = []
    if os.path.isabs(path) is None:
        path = os.path.join(os.path.curdir, path)
    if os.path.exists(path):
        files = os.listdir(path)
        for f in files:
            if os.path.basename(f).endswith('.tar.gz'):
                backups.append(f)
        backups.sort(reverse=True)
    return backups


def latest_backup(path):
    backups = all_backups(path)
    return read_backup(os.path.join(path, backups[0])) \
        if len(backups) > 0 else None


def string_equals(s1, s2):
    """Compare two strings, ignoring case for Windows"""
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        s2 = s2.lower()
    return s1 == s2


def string_contains(s1, s2):
    """Check if one string contains another, ignoring case for Windows"""
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        s2 = s2.lower()
    return s1 in s2


def list_contains(s1, l2, exact_match=True):
    """Check if list contains string, ignoring case for Windows"""
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    return s1 in l2


def get_filename_index(s1, l2):
    """Get index for filename in list contains string, ignoring case for
    Windows and ignoring path. Returns None if not found"""
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    try:
        return map(os.path.basename, l2).index(s1)
    except ValueError:
        return None


def get_config_index(dirlist, src, dest):
    """Find the entry in the config file with the given source and
    destination and return the index.
    Returns None if not found."""
    logger.debug('get index of %s, %s' % (src, dest))
    for i in range(len(dirlist)):
        if (
            len(dirlist[i]) >= 2 and
            string_equals(dirlist[i][0], src) and
            string_equals(dirlist[i][1], dest)
        ):
            return i
    return None


def read_directory_list(path):
    logger.debug('reading directories from config')
    with open(path) as l:
        dirs = []
        for line in l:
            dirs.append(line[:-1].split(','))
    return dirs


def write_directory_list(path, dirlist):
    logger.debug('writing directories to config')
    with open(path, "w+") as l:
        for line in dirlist:
            l.write(','.join(line) + '\n')


def show_directory_list(dirs):
    logger.info('backup directories:')
    for line in dirs:
        if len(line) < 2:
            logger.error('bad config entry:\n%s' % line)
            return
        logger.info('from %s to %s' % (line[0], line[1]))
        skips = ', '.join(line[2:])
        if skips:
            logger.info('  skipping %s' % skips)


def add_directory(path, src, dest):
    """Add new source and destination directories to the config file.
    Make sure paths are absolute, exist, and
    are not already added before adding."""
    logger.debug('adding directories %s, %s to list' % (src, dest))
    dirs = read_directory_list(path)
    if get_config_index(dirs, src, dest) is not None:
        logger.error('%s, %s already added to config file' % (src, dest))
        return
    if not os.path.isabs(src):
        logger.warning('relative path used for source dir, adding current dir')
        src = os.path.abspath(src)
    if not os.path.isabs(dest):
        logger.warning(
            'relative path used for destination dir, adding current dir'
        )
        dest = os.path.abspath(dest)
    # check config file again now paths are absolute
    if get_config_index(dirs, src, dest) is not None:
        logger.error('%s, %s already added to config file' % (src, dest))
        return

    logger.info('adding new entry source: %s, destination: %s' % (src, dest))
    # now check paths exist. dest can be created, but fail if src not found
    if not os.path.exists(src):
        logger.error('source path %s not found' % src)
        return
    if not os.path.exists(dest):
        logger.warning(
            'destination path %s not found, creating directory' % dest
        )
        os.mkdir(dest)

    dirs.append([src, dest])
    write_directory_list(path, dirs)


def delete_directory(path, src, dest):
    logger.info('removing entry source: %s, destination: %s' % (src, dest))
    dirs = read_directory_list(path)
    index = get_config_index(dirs, src, dest)
    if index is None:
        logger.error('entry not found')
        return

    del dirs[index]
    write_directory_list(path, dirs)


def add_skip(path, skips, add_regex=None):
    if len(skips) < 3:
        print 'skip syntax: <src> <dest> <skip dir> {... <skip dir>}'
        print 'source and destination directories must be specified first'
        print 'then one or more skip directories can be added'
        print 'note: -s "(\S)*<string>(\S)*" is equivalent to -c "<string>"'
        return
    dirs = read_directory_list(path)
    src = skips[0]
    dest = skips[1]
    logger.info('adding skips to backup of %s to %s:' % (src, dest))
    index = get_config_index(dirs, src, dest)
    if index is None:
        logger.error('entry not found')
        return

    line = dirs[index]
    for skip in skips[2:]:
        # if 'contains' option is used and regex hasn't already been added,
        # wrap skip string in any character regex
        if add_regex and u'(\S)*' != skip[:5] and u'(\S)*' != skip[-5:]:
            skip = u'(\S)*{0:s}(\S)*'.format(skip)
        if skip in line[2:]:
            logger.error('%s already added, aborting' % skip)
            return
        if skip == line[0]:
            logger.warning('%s would skip root dir, not added' % skip)
        else:
            line.append(skip)
            logger.info('  %s' % skip)

    write_directory_list(path, dirs)


def perform_backup(directories):
    if len(directories) < 2:
        logger.error('not enough directories to backup')
        logger.error(directories)
        return
    src = directories[0]
    dest = directories[1]
    skip = directories[2:] if len(directories) > 2 else None
    logger.info('backup of directory %s to %s' % (src, dest))
    if skip is not None:
        logger.info('  skipping directories that match %s' % ' or '.join(skip))
    f = FileIndex(src, skip)
    f.gen_index()
    backup = Backup(dest, f, latest_backup(dest))
    backup.write_to_disk()


def search_backup(path, file, files, folders, exact_match=True):
    logger.debug('searching %s (exact=%s)' % (path, exact_match))
    last_hash = None
    for zip_path in all_backups(path):
        backup = read_backup(os.path.join(path, zip_path))
        this_hash = backup.contains_file(file, exact_match)
        if this_hash:
            if this_hash != last_hash:
                logger.debug('hash %s#' % this_hash)
                files.append(backup)
                last_hash = this_hash
        else:
            logger.debug('file not found, trying folders')
            # TODO partial match of folder name
            if backup.contains_folder(file):
                logger.debug('appending full zip path')
                folders.append(backup)


def find_file_in_backup(dirlist, file):
    files = []
    folders = []
    searched = []
    found = False

    # try a few times to find file, with less strict criteria on each pass
    for attempt in xrange(4):
        logger.debug('attempt %s' % attempt)
        for dirs in dirlist:
            if 0 == attempt:
                # check if input matches a config entry
                if string_equals(dirs[0], file):
                    logger.debug('restoring all backups from %s' % dirs[0])
                    for zip_path in all_backups(dirs[1]):
                        read_backup(zip_path).restore_folder(file)
                    return

            if 1 == attempt:
                # then look in all folders for exact string entered
                if string_contains(dirs[0], file) or \
                   string_contains(file, dirs[0]):
                    searched.append(dirs)
                    logger.debug('string contains, looking in %s' % dirs[1])
                    search_backup(dirs[1], file, files, folders)

            if 2 == attempt:
                # then look in remaining folders for exact string entered
                if dirs not in searched:
                    logger.debug('dirs not searched, looking in %s' % dirs[1])
                    search_backup(dirs[1], file, files, folders)

            if 3 == attempt:
                # then look again in case partial path given
                logger.debug('looking for partial match in %s' % dirs[1])
                search_backup(
                    dirs[1], file, files, folders, exact_match=False
                )

        if files:
            found = True
            index = 0
            # select version to restore
            if len(files) > 1:
                print 'file %s found in:' % file
                count = 1
                for backup in files:
                    print '[%s] %s' % (count, backup.get_tarpath())
                    count += 1
                # TODO get user to choose
                # update index

            files[index].restore_file(file)
        elif folders:
            found = True
            # restore all folders, oldest first
            folders.reverse()
            for backup in folders:
                backup.restore_folder(file)

        if found:
            logger.debug('files found, returning')
            return

    if not found:
        logger.warning('%s not found' % file)

# fork if no args(all) or specific files/folders
# restore all - for each src,dest from config, get zips in
# reverse order and unzip from dest to src
# specific - try and find file/folder by matching path to
# src paths in config then search zips in that dest folder
# if not found, search again in all zips
# file - list all versions then ask which to restore
# folder - restore all instances of that folder in reverse date order


def perform_restore(dirlist, files):
    if not files:
        # doing restore all
        logger.warning('restore all not implemented')
        # for file in dirlist:
        #     logger.info('  %s' % file[0])

    for file in files:
        # restoring individual files/folders
        logger.debug('looking for %s' % file)
        find_file_in_backup(dirlist, os.path.normpath(file))


def init(file_config):
    logger.debug('opening config file')
    try:
        f = open(file_config)
        f.close()
    except IOError:
        logger.debug('not found, creating new config')
        f = open(file_config, 'w+')
        f.close()


def parse_args():
    parser = ArgumentParser(description='Command line backup utility')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='enable console logging')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list', dest='list', action='store_true',
                       required=False,
                       help='list the all the directories currently in the\
                       config file')
    group.add_argument('-a', '--add', metavar='path', nargs=2,
                       dest='add_path', required=False,
                       help='adds the specified source directory to the\
                       backup index. the backups will be stored in the\
                       specified destination directory.\
                       if relative paths used, the current working directory\
                       will be added.')
    group.add_argument('-b', '--backup', action='store_true', dest='backup',
                       help='performs a backup for all path specified in the\
                       backup.lst file')
    group.add_argument('-s', '--skip', dest='skip', metavar='string',
                       nargs='+', required=False,
                       help='skips all directories that match the given\
                       string(s)')
    group.add_argument('-c', '--contains', dest='contains', metavar='regex',
                       nargs='+', required=False,
                       help='skips all directories that match the given\
                       regular expression')
    group.add_argument('-d', '--delete', metavar='path', nargs=2,
                       dest='delete_path', required=False,
                       help='remove the specified source and destination\
                       directories from the backup.lst file')
    group.add_argument('-r', '--restore', metavar='path', nargs='*',
                       dest='restore', required=False, help='restore selected\
                       files to their original folders. can give full file\
                       path or just the file name. leave blank to restore\
                       all.')
    return vars(parser.parse_args())

if __name__ == '__main__':
    start = datetime.now()
    args = parse_args()

    # set up logging
    logger = logging.getLogger('backpy')
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(SpecialFormatter())
    sh.setLevel(logging.INFO)
    if args['verbose']:
        sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    fh = logging.handlers.RotatingFileHandler(
        os.path.expanduser('~/backpy.log'), maxBytes=1000000, backupCount=3
    )
    fh.setLevel(logging.DEBUG)
    ff = logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s')
    fh.setFormatter(ff)
    logger.addHandler(fh)

    config_file = os.path.expanduser('~/.backpy')
    init(config_file)
    backup_dirs = read_directory_list(config_file)
    if args['list']:
        show_directory_list(backup_dirs)
    elif args['add_path']:
        add_directory(
            config_file, args['add_path'][0], args['add_path'][1]
        )
    elif args['delete_path']:
        delete_directory(
            config_file, args['delete_path'][0], args['delete_path'][1]
        )
    elif args['skip']:
        add_skip(config_file, args['skip'])
    elif args['contains']:
        add_skip(config_file, args['contains'], True)
    elif args['backup']:
        for directory in backup_dirs:
            perform_backup(directory)
            print ''
        logger.info('done. elapsed time = %s' % (datetime.now() - start))
    elif args['restore'] is not None:
        perform_restore(backup_dirs, args['restore'])
        logger.info('done. elapsed time = %s' % (datetime.now() - start))
    else:
        print "please specify a program option.\n" + \
            "invoke with --help for futher information."
