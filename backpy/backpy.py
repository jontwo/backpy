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
__version__ = '1.1'
__copyright__ = 'Simplified BSD license'

import logging
import logging.handlers
import os
import re
import subprocess
import sys
import tarfile
from argparse import ArgumentParser
from datetime import datetime
from hashlib import md5
from pdb import set_trace  # noqa

ROOT_PATH = os.path.abspath(os.sep)
CONFIG_FILE = os.path.expanduser('~/.backpy')
logger = logging.getLogger('backpy')

# android backup mode
global adb
adb = False
ANDROID_SKIPS = os.path.expanduser('~/.androidSkipFolders')


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

    def is_valid(self, f):
        flags = 0
        if os.getenv("OS") == "Windows_NT":
            flags = re.IGNORECASE
        if adb:
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
                if re.match(regex, f, flags=flags) is not None:
                    return False
        return True

    def gen_index(self):
        if adb:
            logger.debug('generating index of android device')
            self.adb_read_folder(self.__path__)
            return

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
                digest = get_file_hash(fullname)
                if digest:
                    self.__files__[fullname] = digest

    def files(self):
        return self.__files__.keys()

    def skips(self):
        return self.__exclusion_rules__

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

    def adb_read_folder(self, path):
        """use adb to list all files and folders in path,
        hashing with full file path, modified date and time, and size"""
        logger.debug('reading adb folder %s' % path)
        # check files in this folder
        for out in subprocess.check_output(
            ['adb', 'shell', 'ls', '-a', '-l', path]
        ).split('\n'):
            file_info = out.strip()
            if not len(file_info):
                continue
            line = file_info.split()
            try:
                f_permissions = line[0]
                # f_owner = line[1]
                # f_group = line[2]
                if not f_permissions.startswith('d'):
                    f_size = line[3]
                    f_date = line[4]
                    f_time = line[5]
                    f_name = ' '.join(line[6:])
                else:
                    f_date = line[3]
                    f_time = line[4]
                    f_name = ' '.join(line[5:])
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
                        digest = get_file_hash(
                            fullname, f_date + f_time, f_size
                        )
                        if digest:
                            self.__files__[fullname] = digest

            except IndexError:
                logger.warning('could not extract info from %s' % file_info)


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
                if adb:
                    # pull files off phone into temp folder before backing up
                    temp_path = os.path.join(
                        '.', '.%s_adb' % self.__timestamp__
                    )
                    # replace file root with temp path
                    temp_name = os.path.abspath(os.path.join(
                        temp_path,
                        f.replace(self.__new_index__.__path__ + '/', '')
                    ))
                    try:
                        subprocess.check_call(
                            ['adb', 'pull', f, temp_name]
                        )
                        # add to tar using original name
                        tar.add(temp_name, f)
                    except subprocess.CalledProcessError:
                        logger.warning('could not pull %s from phone' % f)

                    # delete temp files
                    delete_temp_files(temp_path)
                else:
                    tar.add(f)
                # TODO do not keep index if nothing added?

            # backup current config file
            tar.add(CONFIG_FILE, '.backpy')

    # TODO platform independent paths
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

    def contains_file(self, f, exact_match=True):
        """look for a specific file in the index, return the hash
        if found or None if not"""
        logger.debug('find file %s' % f)
        return self.__new_index__.hash(f, exact_match)

    def contains_folder(self, f):
        """look for a specific folder in the index"""
        logger.debug('find folder %s' % f)
        return self.__new_index__.is_folder(f)

    def restore_folder(self, folder):
        # logger.debug('restoring folder %s' % folder)  # TODO
        pass

        # get destination dir
        # index destination dir
        # diff then restore changed files

        # dest = None
        # for dirs in dirlist:
        #     if string_equals(dirs[1], os.path.dirname(zip_path)):
        #         dest = dirs[0]
        # if dest:
        #     logger.info(
        #         'restoring %s from %s to %s' % (folder, zip_path, dest)
        #     )

    def restore_file(self, filename):
        logger.debug(
            'restoring file %s from %s' % (filename, self.get_tarpath())
        )
        fullname = filename
        # get destination dir
        dest = os.path.dirname(filename)
        if not dest:
            # make sure dest and file are full paths
            index = get_filename_index(filename, self.__new_index__.files())
            if not index:
                logger.error('cannot find file to restore')
                return
            fullname = self.__new_index__.files()[index]
            dest = os.path.dirname(fullname)
        logger.debug('got dest dir %s' % dest)

        # restore if file changed or not found in dest
        if os.path.exists(fullname):
            if get_file_hash(fullname) == self.__new_index__.hash(fullname):
                logger.info('file unchanged, cancelling restore')
                return
            else:
                logger.debug('file changed')
        else:
            logger.debug('file not found')

        with tarfile.open(self.get_tarpath(), 'r:*') as tar:
            member_name = self.get_member_name(fullname)
            logger.info(
                'restoring %s from %s' % (member_name, self.get_tarpath())
            )
            tar.extractall(ROOT_PATH, [tar.getmember(member_name)])

    # noinspection PyMethodMayBeStatic
    def get_member_name(self, name):
        """convert full (source) path of file to path within tar"""
        logger.debug('getting member name for %s' % name)
        member = name.replace(ROOT_PATH, '')
        if os.getenv("OS") == "Windows_NT":
            member = member.replace('\\', '/')

        logger.debug('returning %s' % member)
        return member


def get_file_hash(fullname, size=None, ctime=None):
    """return a string representing the md5 hash of the given file.
    use size and/or ctime args if file is on a phone and can't be read."""
    if size or ctime:
        md5hash = md5(fullname)
        if size:
            md5hash.update(size)
        if ctime:
            md5hash.update(ctime)
    else:
        try:
            with open(fullname) as f:
                md5hash = md5(f.read())
        except IOError:
            logger.warning('could not process file: %s' % fullname)

    return ''.join(
        ['%x' % ord(h) for h in md5hash.digest()]
    ) if md5hash else None


def delete_temp_files(path):
    """Attempt to delete temporary files or folders in the given path.
    Just carry on if any can't be deleted."""
    if os.path.isfile(path):
        # single file - delete it and return
        try:
            os.unlink(path)
        except OSError:
            logger.warning('could not delete %s' % path)
        return

    if os.path.isdir(path):
        # directory - delete subfiles and folders then delete it
        for f in os.listdir(path):
            delete_temp_files(os.path.join(path, f))
        try:
            os.rmdir(path)
        except OSError:
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


def list_contains(s1, l2):
    """Check if list contains string, ignoring case for Windows"""
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    return s1 in l2


def get_filename_index(s1, l2):
    """Get index for filename in list, ignoring case for Windows and
    ignoring path. Returns None if not found"""
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
        if len(dirlist[i]) >= 2:
            # normalise trailing slashes
            src = os.path.normpath(src)
            dest = os.path.normpath(dest)
            index_src = os.path.normpath(dirlist[i][0])
            index_dest = os.path.normpath(dirlist[i][1])
            logger.debug('entry %d: %s, %s.' % (
                i, index_src, index_dest
            ))
            if (
                string_equals(index_src, src) and
                string_equals(index_dest, dest)
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
    # TODO write 3x file separators for windows
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
        if not os.path.isabs(src):
            logger.warning(
                'relative path used for source dir, adding current dir'
            )
            src = os.path.abspath(src)
        if not os.path.isabs(dest):
            logger.warning(
                'relative path used for destination dir, adding current dir'
            )
            dest = os.path.abspath(dest)

        # check config file again now paths are absolute
        index = get_config_index(dirs, src, dest)
        if index is None:
            logger.error('entry not found')
            return

    del dirs[index]
    write_directory_list(path, dirs)


# TODO better solution for skip all subfolders
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
    # check dest exists before indexing
    if not os.path.exists(dest):
        logger.warning(
            'destination path %s not found, creating directory' % dest
        )
        os.mkdir(dest)
    f = FileIndex(src, skip)
    f.gen_index()
    backup = Backup(dest, f, latest_backup(dest))
    backup.write_to_disk()


def search_backup(path, filename, files, folders, exact_match=True):
    """look through all the backups in path for filename,
    returning any files or folders that match.
    set exact_match to false to allow partial matches."""
    logger.debug('searching %s (exact=%s)' % (path, exact_match))
    last_hash = None
    last_backup = None
    # we don't know if user has entered a file or a folder, so search both
    for zip_path in all_backups(path):
        this_backup = read_backup(os.path.join(path, zip_path))
        # note: it's the last (oldest) backup that contains each unique hash
        this_hash = this_backup.contains_file(filename, exact_match)
        if this_hash or last_hash:
            if this_hash != last_hash:
                # hash has changed, so if there is a previous hash,
                # add the previous backup
                logger.debug('hash %s' % this_hash)
                if last_hash:
                    logger.debug('hash changed, adding last backup')
                    files.append(last_backup)
                last_hash = this_hash

        # also see if filename matches any of the folders in this backup
        # TODO partial match of folder name
        if this_backup.contains_folder(filename):
            logger.debug('folder found, adding backup to list')
            folders.append(this_backup)

        last_backup = this_backup


def find_file_in_backup(dirlist, filename):
    files = []
    folders = []
    searched = []

    # try a few times to find file, with less strict criteria on each pass
    for attempt in xrange(4):
        logger.debug('attempt %s' % attempt)
        for dirs in dirlist:
            if 0 == attempt:
                # check if input matches a config entry
                if string_equals(dirs[0], filename):
                    logger.debug('restoring all backups from %s' % dirs[0])
                    for zip_path in all_backups(dirs[1]):
                        read_backup(zip_path).restore_folder(filename)
                    return

            if 1 == attempt:
                # then look in all folders for exact string entered
                if string_contains(dirs[0], filename) or \
                   string_contains(filename, dirs[0]):
                    searched.append(dirs)
                    logger.debug('string contains, looking in %s' % dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 2 == attempt:
                # then look in remaining folders for exact string entered
                if dirs not in searched:
                    logger.debug('dirs not searched, looking in %s' % dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 3 == attempt:
                # then look again in case partial path given
                logger.debug('looking for partial match in %s' % dirs[1])
                search_backup(
                    dirs[1], filename, files, folders, exact_match=False
                )

        # found something, restore it and return
        if files:
            index = 0
            # select version to restore
            if len(files) > 1:
                logger.info('multiple versions of %s found:' % filename)
                count = 1
                for backup in files:
                    logger.info('[%s] %s' % (count, backup.get_tarpath()))
                    count += 1
                logger.info(
                    'please choose a version to restore '
                    '(leave blank to cancel):'
                )
                chosen = ''
                try:
                    chosen = raw_input()
                    if not chosen:
                        return  # user has cancelled restore
                    index = int(chosen) - 1
                    logger.debug('index=%s' % index)
                    # now check index is valid
                    if index < 0:
                        raise IndexError
                    _ = files[index]  # noqa
                except (TypeError, IndexError, ValueError):
                    logger.error('"%s" is not a valid choice' % chosen)
                    return

            files[index].restore_file(filename)
        elif folders:
            # restore all folders, oldest first
            # (should have been discovered in date order)
            folders.reverse()
            for backup in folders:
                backup.restore_folder(filename)

        if files or folders:
            logger.debug('files found, returning')
            return

    logger.warning('%s not found' % filename)


def perform_restore(dirlist, files):
    if not files:
        # doing restore all
        logger.warning('restore all not implemented')  # TODO
        # for file in dirlist:
        #     logger.info('  %s' % file[0])

    for f in files:
        # restoring individual files/folders
        logger.debug('looking for %s' % f)
        find_file_in_backup(dirlist, os.path.normpath(f))


def set_up_logging(level=1):
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(SpecialFormatter())
    sh.setLevel(logging.INFO)
    if 2 == level:
        sh.setLevel(logging.DEBUG)
    # kill console output (i.e. during unit tests)
    if 0 != level:
        logger.addHandler(sh)
    fh = logging.handlers.RotatingFileHandler(
        os.path.expanduser('~/backpy.log'), maxBytes=1000000, backupCount=3
    )
    fh.setLevel(logging.DEBUG)
    ff = logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s')
    fh.setFormatter(ff)
    logger.addHandler(fh)


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
    group.add_argument('-a', '--add', metavar='path', nargs='+',
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
    group.add_argument('-n', '--adb', '--android', nargs=1,
                       dest='adb', metavar='path', required=False,
                       help='backs up the connected android device to the\
                       given folder')
    return vars(parser.parse_args())

if __name__ == '__main__':
    start = datetime.now()
    args = parse_args()

    set_up_logging(2 if args['verbose'] else 1)
    init(CONFIG_FILE)
    backup_dirs = read_directory_list(CONFIG_FILE)
    if args['list']:
        show_directory_list(backup_dirs)
    elif args['add_path']:
        # TODO make into function for use elsewhere
        new_args = []
        if len(args['add_path']) > 2:
            logger.info('More than two args, trying to fix spaces')
            prev_arg = ''
            for arg in args['add_path']:
                if prev_arg != '':
                    prev_arg += ' '
                prev_arg += arg
                if os.path.exists(prev_arg):
                    new_args.append(prev_arg)
                    prev_arg = ''

            if prev_arg and os.path.exists(os.path.dirname(prev_arg)):
                new_args.append(prev_arg)
                logger.debug(
                    "Couldn't find path, but parent dir is found, must be dest"
                )

        elif len(args['add_path']) == 2:
            new_args = args['add_path']
        if len(new_args) > 1:
            add_directory(
                CONFIG_FILE, new_args[0], new_args[1]
            )
        else:
            logger.error('Two valid paths not given')
    elif args['delete_path']:
        delete_directory(
            CONFIG_FILE, args['delete_path'][0], args['delete_path'][1]
        )
    elif args['skip']:
        # TODO skip all subfolders
        add_skip(CONFIG_FILE, args['skip'])
    elif args['contains']:
        add_skip(CONFIG_FILE, args['contains'], True)
    elif args['backup']:
        for directory in backup_dirs:
            print ''
            perform_backup(directory)
    elif args['adb']:
        adb = True
        # TODO optional source dir arg?
        perform_backup(['/sdcard/', args['adb'][0]])
    elif args['restore'] is not None:
        perform_restore(backup_dirs, args['restore'])
    else:
        print "please specify a program option.\n" + \
            "invoke with --help for futher information."

    if args['backup'] or args['restore'] or args['adb']:
        print ''
        logger.info('done. elapsed time = %s' % (datetime.now() - start))
