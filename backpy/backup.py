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

import logging
import os
import subprocess
import tarfile
import tempfile
from contextlib import closing
from datetime import datetime

from .file_index import FileIndex
from .helpers import (
    CONFIG_FILE,
    delete_temp_files,
    get_file_hash,
    get_filename_index,
    get_folder_index,
    is_windows,
    string_startswith,
)
from .logger import LOG_NAME

TEMP_DIR = os.path.join(tempfile.gettempdir(), "backpy")
LOG = logging.getLogger(LOG_NAME)


class Backup:
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
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_index(self):
        """Get this backup's index"""
        return self.__new_index__

    def get_tarpath(self):
        """Get the location of this backup zip on disk"""
        return os.path.join(self.__path__, "%s_backup.tar.gz" % self.__timestamp__)

    def write_to_disk(self):
        """Add all new and modified files to the zip file for this backup"""
        if not self.__new_index__.files():
            LOG.warning("no files to back up")
            return

        LOG.debug("writing files to backup")
        added = 0
        # use closing for python 2.6 compatibility
        with closing(tarfile.open(self.get_tarpath(), "w:gz")) as tar:
            # write index
            path = os.path.join(TEMP_DIR, ".%s_index" % self.__timestamp__)
            self.__new_index__.write_index(path)
            tar.add(path, ".index")
            # delete temp index now we've written it
            delete_temp_files(path)
            # write files
            for fname in self.__new_index__.get_diff(self.__old_index__):
                LOG.info("adding %s...", fname)
                if self.__adb__:  # pragma: no cover
                    # pull files off phone into temp folder before backing up
                    temp_path = os.path.join(TEMP_DIR, ".%s_adb" % self.__timestamp__)
                    # replace file root with temp path
                    temp_name = os.path.join(os.path.abspath(temp_path), fname.replace("/", os.sep))
                    try:
                        process = subprocess.Popen(
                            ["adb", "pull", "-a", fname, temp_name],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                        )
                        output, error = process.communicate()
                        LOG.info(output.strip())
                        if error:
                            LOG.warning(error.strip())
                        # add to tar using original name
                        tar.add(temp_name, fname)
                        added += 1
                    except subprocess.CalledProcessError:
                        LOG.warning("could not pull %s from phone", fname)
                    finally:
                        delete_temp_files(temp_name)

                    # delete temp files
                    delete_temp_files(temp_path)
                else:
                    tar.add(fname)
                    added += 1

            # backup current config file
            if self.__adb__:  # pragma: no cover
                # create dummy file for this backup only
                temp_config = os.path.join(TEMP_DIR, "dummy_config")
                with open(temp_config, "w") as dummy:
                    dummy.write("{0},{1}\n".format(self.__new_index__.__path__, self.__path__))
                tar.add(temp_config, ".backpy")
                # delete dummy file now we've written it
                delete_temp_files(temp_config)
            else:
                tar.add(CONFIG_FILE, ".backpy")

        # do not keep index if nothing added or removed
        removed = self.__new_index__.get_missing(self.__old_index__)
        if added or removed:
            LOG.info("%s files backed up", added)
            LOG.info("%s files removed", len(removed))
        else:
            delete_temp_files(self.get_tarpath())
            LOG.warning("no files changed - nothing to back up")

    def contains_file(self, filename, exact_match=True):
        """
        Look for a specific file in the index
        :param filename: name of file
        :param exact_match: true to match the name exactly, false for partial matches
        :return: the file hash or None if not found
        """
        LOG.debug("find file %s", filename)
        return self.__new_index__.file_hash(filename, exact_match)

    def contains_folder(self, foldername, exact_match=True):
        """
        Look for a specific folder in the index
        :param foldername: name of folder
        :param exact_match: true to match the name exactly, false for partial matches
        :return: true if f is in the index, false if not
        """
        LOG.debug("find folder %s", foldername)
        return self.__new_index__.is_folder(foldername, exact_match)

    def restore_folder(self, folder, restore_path=None):
        """
        Restore the selected folder to its original location on disk
        :param folder: Name of folder to restore
        :param restore_path: An alternative location to restore to
        """
        LOG.debug("restoring folder %s from %s", folder, self.get_tarpath())
        fullname = folder
        # get destination dir
        dest = os.path.dirname(folder)
        if not dest:
            # make sure dest and file are full paths
            index = get_folder_index(folder, self.__new_index__.dirs())
            if index is None:
                LOG.error("cannot find folder to restore")
                return
            fullname = self.__new_index__.dirs()[index]
            dest = os.path.dirname(fullname)
        LOG.debug("got dest dir %s", dest)

        # index destination dir
        dest_index = FileIndex(fullname, adb=self.__adb__)
        dest_index.gen_index()

        # restore changed and missing files
        for dest_file in self.__new_index__.files():
            if string_startswith(fullname, dest_file) and (
                dest_index.file_hash(dest_file) != self.__new_index__.file_hash(dest_file)
                or dest_file not in dest_index.files()
            ):
                self.restore_file(dest_file, restore_path)

    def restore_file(self, filename, restore_path=None):
        """
        Restore the selected file to its original location on disk
        :param filename: Name of file to restore
        :param restore_path: An alternative location to restore to
        """
        LOG.debug("restoring file %s from %s", filename, self.get_tarpath())
        fullname = filename
        # get destination dir
        dest = os.path.dirname(filename)
        if not dest:
            # make sure dest and file are full paths
            index = get_filename_index(filename, self.__new_index__.files())
            if index is None:
                LOG.error("cannot find file to restore")
                return
            fullname = self.__new_index__.files()[index]
            dest = os.path.dirname(fullname)
        LOG.debug("got dest dir %s", dest)

        # restore if file changed or not found in dest
        root_path, member_name = self.get_member_name(fullname)
        if restore_path is not None:
            # override root if restoring to temp folder
            root_path = restore_path
        dest_path = os.path.join(root_path, member_name)
        if os.path.exists(dest_path):
            if get_file_hash(dest_path) == self.__new_index__.file_hash(fullname):
                LOG.info("file unchanged, cancelling restore")
                return
            else:
                LOG.debug("file changed")
        else:
            LOG.debug("file not found")

        LOG.info("restoring %s from %s", member_name, self.get_tarpath())
        with closing(tarfile.open(self.get_tarpath(), "r:*")) as tar:
            if self.__adb__:  # pragma: no cover
                # extract files into temp folder before restoring to phone
                file_info = tar.getmember(member_name)
                temp_path = os.path.join(TEMP_DIR, ".%s_adb" % self.__timestamp__)
                temp_name = os.path.join(
                    os.path.abspath(temp_path), file_info.name.replace("/", os.sep)
                )
                try:
                    LOG.debug("extracting %s to temp path %s", file_info.name, temp_path)
                    tar.extractall(temp_path, [file_info])
                    process = subprocess.Popen(
                        ["adb", "push", temp_name, fullname],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    output, error = process.communicate()
                    LOG.info(output.strip())
                    if error:
                        LOG.warning(error.strip())
                except subprocess.CalledProcessError:
                    LOG.warning("could not push %s to phone", temp_name)
                except KeyError:
                    # file may be in index but not backed up as it was unchanged from prev backup
                    LOG.info("%s not found in this backup", os.path.basename(member_name))
                finally:
                    delete_temp_files(temp_name)

                # delete temp files
                delete_temp_files(temp_path)
            else:
                try:
                    LOG.debug("extracting %s to %s", tar.getmember(member_name), root_path)
                    tar.extractall(root_path, [tar.getmember(member_name)])
                    LOG.debug(os.listdir(root_path))
                except KeyError:
                    # file may be in index but not backed up as it was unchanged from prev backup
                    LOG.info("%s not found in this backup", os.path.basename(member_name))

    @staticmethod
    def get_member_name(name):
        """
        Convert full (source) path of file to path within tar
        :param name: full path of file
        :return: member name of file
        """
        LOG.debug("getting member name for %s", name)
        # splitdrive returns ['c:', '\path\to\member'] when we want ['c:\', 'path\to\member']
        split_member = os.path.splitdrive(name)
        root = split_member[0] + split_member[1][:1]
        member = split_member[1][1:]

        if is_windows():
            member = member.replace("\\", "/")

        LOG.debug("returning %s, %s", root, member)
        return root, member
