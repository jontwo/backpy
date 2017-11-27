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
import os
import re
import tarfile
from argparse import ArgumentParser
from contextlib import closing
from datetime import datetime

# Project imports
from backup import Backup, CONFIG_FILE, TEMP_DIR
from file_index import FileIndex
from helpers import delete_temp_files, string_equals, string_contains, handle_arg_spaces, make_directory
from logger import logger, set_up_logging

__author__ = 'Steffen Schneider'
__version__ = '1.4.7'
__copyright__ = 'Simplified BSD license'


def read_backup(path):
    logger.debug('reading backup %s' % path)
    timestamp = os.path.basename(path).split('_')[0]
    temp_path = os.path.join(TEMP_DIR, '.%sindex' % timestamp)
    try:
        with closing(tarfile.open(path, 'r:*')) as tar:
            tar.extract('.index', temp_path)
    except Exception as e:
        logger.error(e.message)
    finally:
        index = FileIndex(temp_path, reading=True)
        index.read_index(os.path.join(temp_path, '.index'))
        # delete temp index now we've read it
        delete_temp_files(temp_path)
        return Backup(os.path.dirname(path), index, timestamp=timestamp)


def all_backups(path, reverse_order=True):
    logger.debug('finding previous backups')
    backups = []
    if os.path.isabs(path) is None:
        path = os.path.join(os.path.curdir, path)
    if os.path.exists(path):
        files = os.listdir(path)
        for f in files:
            if os.path.basename(f).endswith('.tar.gz'):
                backups.append(f)
        backups.sort(reverse=reverse_order)
    return backups


def latest_backup(path):
    backups = all_backups(path)
    if not backups:
        return None
    last_backup = backups[0]
    logger.info('reading latest backup ({0}) for comparison'.format(last_backup))
    return read_backup(os.path.join(path, last_backup))


def get_config_index(dirlist, src, dest):
    """
    Find the entry in the config file with the given source and destination.
    :param dirlist: list of entries from config file
    :param src: source directory
    :param dest: destination directory
    :return: index number of file or None if not found
    """
    logger.debug('get index of %s, %s' % (src, dest))
    for i in range(len(dirlist)):
        if len(dirlist[i]) >= 2:
            # normalise trailing slashes
            src = os.path.normpath(src)
            dest = os.path.normpath(dest)
            index_src = os.path.normpath(dirlist[i][0])
            index_dest = os.path.normpath(dirlist[i][1])
            logger.debug('entry %d: %s, %s.' % (i, index_src, index_dest))
            if string_equals(index_src, src) and string_equals(index_dest, dest):
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
    index = 1
    for line in dirs:
        if len(line) < 2:
            logger.error('bad config entry:\n%s' % line)
            return
        logger.info('[{0}] from {1} to {2}'.format(index, line[0], line[1]))
        index += 1
        skips = ', '.join(line[2:])
        if skips:
            logger.info('  skipping %s' % skips)


def add_directory(path, src, dest):
    """
    Add new source and destination directories to the config file.
    Make sure paths are absolute, exist, and are not already added before adding.
    :param path: path to config file
    :param src: source directory
    :param dest: destination directory
    """
    logger.debug('adding directories %s, %s to list' % (src, dest))
    dirs = read_directory_list(path)
    if get_config_index(dirs, src, dest) is not None:
        logger.error('%s, %s already added to config file' % (src, dest))
        return
    if not os.path.isabs(src):
        logger.warning('relative path used for source dir, adding current dir')
        src = os.path.abspath(src)
    if not os.path.isabs(dest):
        logger.warning('relative path used for destination dir, adding current dir')
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
        logger.warning('destination path %s not found, creating directory' % dest)
        make_directory(dest)
        if not os.path.exists(dest):
            # make directory failed
            return

    dirs.append([src, dest])
    write_directory_list(path, dirs)


def delete_directory(path, src, dest, confirm=True):
    logger.debug('removing entry source: %s, destination: %s' % (src, dest))
    dirs = read_directory_list(path)
    index = get_config_index(dirs, src, dest)
    if index is None:
        if not os.path.isabs(src):
            logger.warning('relative path used for source dir, adding current dir')
            src = os.path.abspath(src)
        if not os.path.isabs(dest):
            logger.warning('relative path used for destination dir, adding current dir')
            dest = os.path.abspath(dest)

        # check config file again now paths are absolute
        index = get_config_index(dirs, src, dest)
        if index is None:
            logger.error('entry not found')
            return
    delete_directory_by_index(path, index, dirs, confirm)


def delete_directory_by_index(path, index, dirs, confirm=True):
    if dirs is None:
        dirs = read_directory_list(path)

    try:
        if confirm:
            answer = raw_input(
                'delete entry source: {0}, destination: {1} (y/n)?'.format(dirs[index][0],
                                                                           dirs[index][1]))
            if answer.lower() != 'y':
                return
        del dirs[index]
    except IndexError:
        logger.error('index is invalid')
    write_directory_list(path, dirs)


def add_skip(path, skips, add_regex=None):
    if len(skips) < 3:
        print 'skip syntax: <src> <dest> <skip dir> {... <skip dir>}'
        print 'source and destination directories must be specified first'
        print 'then one or more skip directories can be added'
        print 'note: -s "*<string>*" is equivalent to -c "<string>"'
        return
    dirs = read_directory_list(path)
    src = skips[0]
    dest = skips[1]
    logger.info('adding skips to backup of %s to %s:' % (src, dest))
    if not os.path.isabs(src):
        logger.warning('relative path used for source dir, adding current dir')
        src = os.path.abspath(src)
    if not os.path.isabs(dest):
        logger.warning('relative path used for destination dir, adding current dir')
        dest = os.path.abspath(dest)
    index = get_config_index(dirs, src, dest)
    if index is None:
        logger.error('entry not found')
        return

    line = dirs[index]
    for skip in skips[2:]:
        # if 'contains' option is used and regex hasn't already been added,
        # wrap skip string in any character regex
        if add_regex and u'*' != skip[0] and u'*' != skip[-1]:
            skip = u'*{0:s}*'.format(skip)
        if skip in line[2:]:
            logger.error('%s already added, aborting' % skip)
            return
        if skip == line[0]:
            logger.warning('%s would skip root dir, not added' % skip)
        else:
            line.append(skip)
            logger.info('  %s' % skip)

    write_directory_list(path, dirs)


def perform_backup(directories, timestamp=None, adb=False):
    if len(directories) < 2:
        logger.error('not enough directories to backup')
        logger.error(directories)
        return
    src = directories[0]
    dest = directories[1]
    skip = directories[2:] if len(directories) > 2 else None
    logger.info('backup of directory {0} to {1}{2}'.format(src, dest, ' using adb' if adb else ''))
    if skip is not None:
        logger.info('  skipping directories that match %s' % ' or '.join(skip))
    # check dest exists before indexing
    if not os.path.exists(dest):
        logger.warning('destination path %s not found, creating directory' % dest)
        make_directory(dest)
        if not os.path.exists(dest):
            # make directory failed
            return
    f = FileIndex(src, skip, adb=adb)
    f.gen_index()
    backup = Backup(dest, f, latest_backup(dest), timestamp)
    backup.write_to_disk()


def search_backup(path, filename, files, folders, exact_match=True):
    """
    Look through all the backups in path for filename, returning any files or folders that match.
    :param path: backup folder
    :param filename: name of file to search for
    :param files: array of file names
    :param folders: array of folder names
    :param exact_match: true to match the name exactly, false for partial matches
    """
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
                if last_hash is not None:
                    # hash has changed, so add the backup
                    logger.debug('hash %s changed, adding backup' % last_hash)
                    files.append(last_backup)
                last_hash = this_hash
        last_backup = this_backup

        # also see if filename matches any of the folders in this backup
        if this_backup.contains_folder(filename, exact_match):
            logger.debug('folder found, adding backup to list')
            folders.append(this_backup)
    # check if oldest backup needs to be added
    if last_hash is not None:
        logger.debug('hash %s changed, adding backup' % last_hash)
        files.append(last_backup)


def find_file_in_backup(dirlist, filename, index=None):
    """
    Look through all previous backups to find files or folders to restore
    :param dirlist: list of source/destination pairs to search through (taken from config file)
    :param filename: file or folder name to search for. can be full path or just part of the name
    :param index: used for unit testing. when multiple versions of a file are available,
    automatically pick a specific backup. if not given, the user will be prompted for the version
    to restore
    """
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
                        read_backup(os.path.join(dirs[1], zip_path)).restore_folder(filename)
                    return

            if 1 == attempt:
                # then look in all folders for exact string entered
                if string_contains(dirs[0], filename) or string_contains(filename, dirs[0]):
                    searched.append(dirs)
                    logger.debug('string contains, looking in %s' % dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 2 == attempt:
                # then look in remaining folders for exact string entered
                if dirs not in searched:
                    logger.debug('dirs not searched, looking in %s' % dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 3 == attempt:
                # then look in all folders again in case partial path given
                logger.debug('looking for partial match in %s' % dirs[1])
                search_backup(dirs[1], filename, files, folders, exact_match=False)

        # found something, restore it and return
        if files:
            # select version to restore
            if len(files) > 1:
                logger.info('multiple versions of %s found:' % filename)
                count = 1
                for backup in files:
                    logger.info('[%s] %s' % (count, backup.get_tarpath()))
                    count += 1
                if index is None:
                    chosen = ''
                    try:
                        chosen = raw_input(
                            'please choose a version to restore (leave blank to cancel):')
                        if not chosen:
                            return  # user has cancelled restore
                        index = int(chosen) - 1
                        logger.debug('index=%s' % index)
                        # now check index is valid
                        if index < 0 or index >= len(files):
                            raise IndexError
                    except (TypeError, IndexError, ValueError):
                        logger.error('"%s" is not a valid choice' % chosen)
                        return
            else:
                logger.debug('one version of {0} found'.format(filename))
                if index is not None:
                    logger.warning('ignoring index {0} and defaulting to 0'.format(index))
                index = 0
            try:
                files[index].restore_file(filename)
            except IndexError:
                logger.error('index %s is not valid' % index)
                return
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


def perform_restore(dirlist, files=None, chosen_index=None):
    if not files:
        logger.debug('restoring all files')
        if chosen_index:
            logger.warning('restoring all files but index given, chosen index will be reset to 0')
        for dirs in dirlist:
            # restore each file present at time of last backup
            latest = latest_backup(dirs[1])
            for f in latest.get_index().files():
                find_file_in_backup([dirs], f, 0)

            # check all folders are present (i.e. empty folders)
            for f in latest.get_index().dirs():
                if not os.path.exists(f):
                    make_directory(f)
    else:
        # check if first arg is an index
        match_index = re.match('#(\d+)', files[0])
        if match_index:
            try:
                # remove index from files arg
                files = files[1:]
                # reduce dirlist to chosen entry only
                list_index = int(match_index.group(1))
                dirlist = [dirlist[list_index - 1]]
            except (IndexError, TypeError):
                logger.warning('restore index not valid: {0}'.format(match_index.groups()))
                return
        for f in files:
            # restoring individual files/folders
            logger.debug('looking for %s' % f)
            # REMOVED: find_file_in_backup(dirlist, os.path.normpath(f), chosen_index)
            # don't think normpath is needed, and it messes up adb
            find_file_in_backup(dirlist, f, chosen_index)


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
                        help='enable verbose logging')
    parser.add_argument('--version', action='store_true', dest='show_version', help='show version')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list', dest='list', action='store_true', required=False,
                       help='list the all the directories currently in the config file, with '
                            'index number')
    group.add_argument('-a', '--add', metavar='path', nargs='+', dest='add_path', required=False,
                       help='adds the specified source directory to the backup index. the backups '
                            'will be stored in the specified destination directory. if relative '
                            'paths used, the current working directory will be added.')
    group.add_argument('-b', '--backup', action='store_true', dest='backup',
                       help='performs a backup for all paths specified in the backup.lst file')
    group.add_argument('-s', '--skip', dest='skip', metavar='string', nargs='+', required=False,
                       help='skips all directories that match the given fnmatch expression, e.g. '
                            'skip all subdirectories with <source dir>\*\*')
    group.add_argument('-c', '--contains', dest='contains', metavar='string', nargs='+',
                       required=False,
                       help='skips all directories that match the given fnmatch expression')
    group.add_argument('-d', '--delete', metavar='path', nargs='+', dest='delete_path',
                       required=False,
                       help='remove the specified source and destination directories from the '
                            'backup.lst file. can also specify directories by index (see list).')
    group.add_argument('-r', '--restore', metavar='path', nargs='*', dest='restore', required=False,
                       help='restore selected files to their original folders. can give full file '
                            'path or just the file name. leave blank to restore all. using #n as '
                            'first argument limits the search to just the config entry with the '
                            'given index (see list).')
    group.add_argument('-n', '--adb', '--android', nargs='+', dest='adb', metavar='path',
                       required=False,
                       help='backs up the connected android device to the given folder. defaults '
                            'to copying from /sdcard/, but can optionally specify source folder as '
                            'a second argument.')
    return vars(parser.parse_args())


def run_backpy(args):
    start = datetime.now()
    set_up_logging(2 if args['verbose'] else 1)
    init(CONFIG_FILE)
    backup_dirs = read_directory_list(CONFIG_FILE)
    if (args['backup'] or args['restore'] or args['adb']) and not os.path.exists(TEMP_DIR):
        make_directory(TEMP_DIR)
    if args['show_version']:
        logger.info('backpy version: %s' % __version__)
    elif args['list']:
        show_directory_list(backup_dirs)
    elif args['add_path']:
        new_args = handle_arg_spaces(args['add_path'])
        if len(new_args) > 1:
            add_directory(CONFIG_FILE, new_args[0], new_args[1])
        else:
            logger.error('two valid paths not given')
    elif args['delete_path']:
        new_args = handle_arg_spaces(args['delete_path'])
        if len(new_args) > 1:
            delete_directory(CONFIG_FILE, new_args[0], new_args[1])
        else:
            try:
                index = int(new_args[0])
                dirs = read_directory_list(CONFIG_FILE)
                delete_directory_by_index(CONFIG_FILE, index - 1, dirs)
            except (ValueError, IndexError):
                logger.error('two valid paths not given or index is invalid')
    elif args['skip']:
        add_skip(CONFIG_FILE, args['skip'])
    elif args['contains']:
        add_skip(CONFIG_FILE, args['contains'], True)
    elif args['backup']:
        for directory in backup_dirs:
            print ''
            perform_backup(directory)
    elif args['adb']:
        source = '/sdcard/'
        if len(args['adb']) > 1:
            source = args['adb'][1]
        perform_backup([source, args['adb'][0]], adb=True)
    elif args['restore'] is not None:
        perform_restore(backup_dirs, args['restore'])
    else:
        print "please specify a program option.\n" + \
              "invoke with --help for futher information."

    if args['backup'] or args['restore'] or args['adb']:
        print ''
        logger.info('done. elapsed time = %s' % (datetime.now() - start))


if __name__ == '__main__':
    run_backpy(parse_args())
else:
    set_up_logging(0)  # set up default logging on import
