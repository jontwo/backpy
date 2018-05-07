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
import subprocess
import tarfile
import tempfile
from contextlib import closing
from datetime import datetime

# Project imports
from file_index import FileIndex
from helpers import (
    CONFIG_FILE,
    delete_temp_files,
    get_file_hash,
    get_filename_index,
    get_folder_index,
    string_startswith,
    is_windows
)
from logger import logger

TEMP_DIR = os.path.join(tempfile.gettempdir(), 'backpy')


class Backup(object):
    """Backup class
    Manages file handling during backup and restore
    """
    def __init__(self, path, index, parent=None, timestamp=None):
        self.__path__ = path
        self.__timestamp__ = timestamp or self.get_timestamp()
        self.__old_index__ = parent.__new_index__ if parent else None
        self.__new_index__ = index
        self.__adb__ = index.__adb__

    @staticmethod
    def get_timestamp():
        """
        Static method to allow mocking of timestamp during unit tests
        :return: current time in format 19800101120000
        """
        return datetime.now().strftime('%Y%m%d%H%M%S')

    def get_index(self):
        """Get this backup's index"""
        return self.__new_index__

    def get_tarpath(self):
        """Get the location of this backup zip on disk"""
        return os.path.join(self.__path__, '%s_backup.tar.gz' % self.__timestamp__)

    def write_to_disk(self):
        """Add all new and modified files to the zip file for this backup"""
        if not self.__new_index__.files():
            logger.warning('no files to back up')
            return

        logger.debug('writing files to backup')
        added = 0
        # use closing for python 2.6 compatibility
        with closing(tarfile.open(self.get_tarpath(), 'w:gz')) as tar:
            # write index
            path = os.path.join(TEMP_DIR, '.%s_index' % self.__timestamp__)
            self.__new_index__.write_index(path)
            tar.add(path, '.index')
            # delete temp index now we've written it
            delete_temp_files(path)
            # write files
            for fname in self.__new_index__.get_diff(self.__old_index__):
                logger.info('adding %s...', fname)
                if self.__adb__:
                    # pull files off phone into temp folder before backing up
                    temp_path = os.path.join(TEMP_DIR, '.%s_adb' % self.__timestamp__)
                    # replace file root with temp path
                    temp_name = os.path.join(os.path.abspath(temp_path), fname.replace('/', os.sep))
                    try:
                        process = subprocess.Popen(
                            ['adb', 'pull', '-a', fname, temp_name],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                        )
                        output, error = process.communicate()
                        logger.info(output.strip())
                        if error:
                            logger.warning(error.strip())
                        # add to tar using original name
                        tar.add(temp_name, fname)
                        added += 1
                    except subprocess.CalledProcessError:
                        logger.warning('could not pull %s from phone', fname)
                    finally:
                        delete_temp_files(temp_name)

                    # delete temp files
                    delete_temp_files(temp_path)
                else:
                    tar.add(fname)
                    added += 1

            # backup current config file
            if self.__adb__:
                # create dummy file for this backup only
                temp_config = os.path.join(TEMP_DIR, 'dummy_config')
                with open(temp_config, 'w') as dummy:
                    dummy.write('{0},{1}\n'.format(self.__new_index__.__path__, self.__path__))
                tar.add(temp_config, '.backpy')
                # delete dummy file now we've written it
                delete_temp_files(temp_config)
            else:
                tar.add(CONFIG_FILE, '.backpy')

        # do not keep index if nothing added or removed
        removed = self.__new_index__.get_missing(self.__old_index__)
        if added or removed:
            logger.info('%s files backed up', added)
            logger.info('%s files removed', len(removed))
        else:
            delete_temp_files(self.get_tarpath())
            logger.warning('no files changed - nothing to back up')

    def contains_file(self, filename, exact_match=True):
        """
        Look for a specific file in the index
        :param f: name of file
        :param exact_match: true to match the name exactly, false for partial matches
        :return: the file hash or None if not found
        """
        logger.debug('find file %s', filename)
        return self.__new_index__.hash(filename, exact_match)

    def contains_folder(self, foldername, exact_match=True):
        """
        Look for a specific folder in the index
        :param f: name of folder
        :param exact_match: true to match the name exactly, false for partial matches
        :return: true if f is in the index, false if not
        """
        logger.debug('find folder %s', foldername)
        return self.__new_index__.is_folder(foldername, exact_match)

    def get_missing_files(self):
        """
        Find all the files that have been removed since the last backup
        :return: list of missing files
        """
        return filter(lambda x: x not in self.__old_index__, self.__new_index__)

    def restore_folder(self, folder):
        logger.debug('restoring folder %s from %s' % (folder, self.get_tarpath()))
        fullname = folder
        # get destination dir
        dest = os.path.dirname(folder)
        if not dest:
            # make sure dest and file are full paths
            index = get_folder_index(folder, self.__new_index__.dirs())
            if index is None:
                logger.error('cannot find folder to restore')
                return
            fullname = self.__new_index__.dirs()[index]
            dest = os.path.dirname(fullname)
        logger.debug('got dest dir %s', dest)

        # index destination dir
        dest_index = FileIndex(fullname, adb=self.__adb__)
        dest_index.gen_index()

        # restore changed and missing files
        for dest_file in self.__new_index__.files():
            if string_startswith(fullname, dest_file) and (
                dest_index.hash(dest_file) != self.__new_index__.hash(dest_file) or
                dest_file not in dest_index.files()
            ):
                self.restore_file(dest_file)

    def restore_file(self, filename):
        logger.debug('restoring file %s from %s' % (filename, self.get_tarpath()))
        fullname = filename
        # get destination dir
        dest = os.path.dirname(filename)
        if not dest:
            # make sure dest and file are full paths
            index = get_filename_index(filename, self.__new_index__.files())
            if index is None:
                logger.error('cannot find file to restore')
                return
            fullname = self.__new_index__.files()[index]
            dest = os.path.dirname(fullname)
        logger.debug('got dest dir %s', dest)

        # restore if file changed or not found in dest
        if os.path.exists(fullname):
            if get_file_hash(fullname) == self.__new_index__.hash(fullname):
                logger.info('file unchanged, cancelling restore')
                return
            else:
                logger.debug('file changed')
        else:
            logger.debug('file not found')

        with closing(tarfile.open(self.get_tarpath(), 'r:*')) as tar:
            root_path, member_name = self.get_member_name(fullname)
            logger.info('restoring %s from %s' % (member_name, self.get_tarpath()))
            if self.__adb__:
                # extract files into temp folder before restoring to phone
                file_info = tar.getmember(member_name)
                temp_path = os.path.join(TEMP_DIR, '.%s_adb' % self.__timestamp__)
                temp_name = os.path.join(os.path.abspath(temp_path),
                                         file_info.name.replace('/', os.sep))
                try:
                    logger.debug(
                        'extracting %s to temp path %s', file_info.name, temp_path)
                    tar.extractall(temp_path, [file_info])
                    process = subprocess.Popen(
                        ['adb', 'push', temp_name, fullname],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                    )
                    output, error = process.communicate()
                    logger.info(output.strip())
                    if error:
                        logger.warning(error.strip())
                except subprocess.CalledProcessError:
                    logger.warning('could not push %s to phone', temp_name)
                except KeyError:
                    # file may be in index but not backed up as it was unchanged from prev backup
                    logger.info('%s not found in this backup', os.path.basename(member_name))
                finally:
                    delete_temp_files(temp_name)

                # delete temp files
                delete_temp_files(temp_path)
            else:
                try:
                    logger.debug('extracting %s to %s', tar.getmember(member_name), root_path)
                    tar.extractall(root_path, [tar.getmember(member_name)])
                    logger.debug(os.listdir(root_path))
                except KeyError:
                    # file may be in index but not backed up as it was unchanged from prev backup
                    logger.info('%s not found in this backup', os.path.basename(member_name))

    @staticmethod
    def get_member_name(name):
        """
        Convert full (source) path of file to path within tar
        :param name: full path of file
        :return: member name of file
        """
        logger.debug('getting member name for %s', name)
        # splitdrive returns ['c:', '\path\to\member'] when we want ['c:\', 'path\to\member']
        split_member = os.path.splitdrive(name)
        root = split_member[0] + split_member[1][:1]
        member = split_member[1][1:]

        if is_windows():
            member = member.replace('\\', '/')

        logger.debug('returning %s, %s', root, member)
        return root, member
