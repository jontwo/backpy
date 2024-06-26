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
import re
import tarfile
from argparse import ArgumentParser
from contextlib import closing
from datetime import datetime
from importlib.metadata import version

from .backup import TEMP_DIR, Backup
from .file_index import FileIndex
from .helpers import (
    CONFIG_FILE,
    DEFAULT_KEY,
    SKIP_KEY,
    VERSION_KEY,
    delete_temp_files,
    get_config_key,
    get_config_version,
    handle_arg_spaces,
    list_contains,
    make_directory,
    string_contains,
    string_equals,
    update_config_file,
)
from .logger import LOG_NAME, set_up_logging

LOG = logging.getLogger(LOG_NAME)


def read_backup(path):
    """
    Read a backup from disk and return as a Backup object.
    :param path: Path of backup tarfile.
    :return: Opened Backup object.
    """
    LOG.debug("Reading backup %s", path)
    timestamp = os.path.basename(path).split("_")[0]
    temp_path = os.path.join(TEMP_DIR, ".%sindex" % timestamp)
    try:
        with closing(tarfile.open(path, "r:*")) as tar:
            tar.extract(".index", temp_path)
    except (OSError, tarfile.TarError):  # pragma: no cover
        LOG.exception("Could not read backup")

    index = FileIndex(temp_path, reading=True)
    index.read_index(os.path.join(temp_path, ".index"))
    # delete temp index now we've read it
    delete_temp_files(temp_path)
    return Backup(os.path.dirname(path), index, timestamp=timestamp)


def all_backups(path, reverse_order=True):
    """
    Find all the backups in a directory.
    :param path: Directory to search for backup tarfiles.
    :param reverse_order: Whether to return backup paths in reverse order.
    :return: A list of file paths.
    """
    LOG.debug("Finding previous backups.")
    backups = []
    if os.path.isabs(path) is None:
        path = os.path.join(os.path.curdir, path)
    if os.path.exists(path):
        files = os.listdir(path)
        for f in files:
            if os.path.basename(f).endswith(".tar.gz"):
                backups.append(f)
        backups.sort(reverse=reverse_order)
    return backups


def latest_backup(path):
    """
    Find the newest backup in a directory.
    :param path: Directory to search for backup tarfiles.
    :return: Backup object of the newest backup in the directory or None if no backups found.
    """
    backups = all_backups(path)
    if not backups:
        return None
    last_backup = backups[0]
    LOG.info("Reading latest backup (%s) for comparison", last_backup)
    return read_backup(os.path.join(path, last_backup))


def get_config_index(dirlist, src, dest):
    """
    Find the entry in the config file with the given source and destination.
    :param dirlist: List of entries from config file.
    :param src: Path to source directory.
    :param dest: Path to destination directory.
    :return: Index number of file or None if not found.
    """
    LOG.debug("Get index of %s, %s", src, dest)
    for i in range(len(dirlist)):
        if len(dirlist[i]) >= 2:
            # normalise trailing slashes
            src = os.path.normpath(src)
            dest = os.path.normpath(dest)
            index_src = os.path.normpath(dirlist[i][0])
            index_dest = os.path.normpath(dirlist[i][1])
            LOG.debug("Entry %d: %s, %s.", i, index_src, index_dest)
            if string_equals(index_src, src) and string_equals(index_dest, dest):
                return i


def read_directory_list(path):
    """
    Get a list of directories from config file.
    :param path: Path to config file.
    :return: List of directories found in config file.
    """
    LOG.debug("Reading directories from config")
    dirs = []
    for line in get_config_key(path, DEFAULT_KEY):
        dirs.append(line.split(","))
    return dirs


def write_directory_list(path, dirlist):
    """
    Write a list of directories to config file.
    :param path: Path to config file.
    :param dirlist: Directories to write to the config.
    """
    LOG.debug("Writing directories to config")
    update_config_file(path, DEFAULT_KEY, [",".join(line) for line in dirlist])


def show_directory_list(dirs):  # pragma: no cover
    """
    Pretty print a list of directories and skips.
    :param dirs: List of directories to print.
    """
    LOG.info("backup directories:")
    index = 1
    for line in dirs:
        if len(line) < 2:
            LOG.error("bad config entry:\n%s", line)
            return
        LOG.info("[%s] from %s to %s", index, line[0], line[1])
        index += 1
        skips = ", ".join(line[2:])
        if skips:
            LOG.info("  skipping %s", skips)

    global_skips = get_config_key(CONFIG_FILE, SKIP_KEY)
    if global_skips:
        LOG.info("global skips: %s", global_skips[0])


def add_directory(path, src, dest):
    """
    Add new source and destination directories to the config file.
    Make sure paths are absolute, exist, and are not already added before adding.
    :param path: Path to config file.
    :param src: Path to source directory.
    :param dest: Path to destination directory.
    """
    LOG.debug("Adding directories %s, %s to list", src, dest)
    dirs = read_directory_list(path)
    if get_config_index(dirs, src, dest) is not None:
        LOG.error("%s, %s already added to config file", src, dest)
        return
    if not os.path.isabs(src):
        LOG.warning("Relative path used for source dir, adding current dir")
        src = os.path.abspath(src)
    if not os.path.isabs(dest):
        LOG.warning("Relative path used for destination dir, adding current dir")
        dest = os.path.abspath(dest)
    # check config file again now paths are absolute
    if get_config_index(dirs, src, dest) is not None:
        LOG.error("%s, %s already added to config file", src, dest)
        return

    LOG.info("Adding new entry source: %s, destination: %s", src, dest)
    # now check paths exist. dest can be created, but fail if src not found
    if not os.path.exists(src):
        LOG.error("Source path %s not found", src)
        return
    if not os.path.exists(dest):
        LOG.warning("Destination path %s not found, creating directory", dest)
        make_directory(dest)
        if not os.path.exists(dest):
            # make directory failed
            return

    dirs.append([src, dest])
    write_directory_list(path, dirs)


def delete_directory(path, src, dest, confirm=True):
    """
    Remove source and destination directories from the config file.
    :param path: Path to config file.
    :param src: Path to source directory.
    :param dest: Path to destination directory.
    :param confirm: If True, ask user to confirm deletion.
    """
    LOG.debug("Removing entry source: %s, destination: %s", src, dest)
    dirs = read_directory_list(path)
    index = get_config_index(dirs, src, dest)
    if index is None:
        index = _make_paths_absolute_and_get_index(dirs, src, dest)
        if index is None:
            return
    delete_directory_by_index(path, index, dirs, confirm)


def _make_paths_absolute_and_get_index(dirs, src, dest):
    if not os.path.isabs(src):
        LOG.warning("Relative path used for source dir, adding current dir")
        src = os.path.abspath(src)
    if not os.path.isabs(dest):
        LOG.warning("Relative path used for destination dir, adding current dir")
        dest = os.path.abspath(dest)

    # check config file again now paths are absolute
    index = get_config_index(dirs, src, dest)
    if index is None:
        LOG.error("Entry not found")
        return

    return index


def delete_directory_by_index(path, index, dirs=None, confirm=True):
    """
    Remove a directory entry from the config file.
    :param path: Path to config file.
    :param index: Index of entry to remove.
    :param dirs: List of source and dest dirs. can be read from path if not given.
    :param confirm: If True, ask user to confirm deletion.
    """
    if dirs is None:
        dirs = read_directory_list(path)

    try:
        if confirm:  # pragma: no cover
            answer = input(
                "Delete entry source: {0}, destination: {1} (y/n)?".format(
                    dirs[index][0], dirs[index][1]
                )
            )
            if answer.lower() != "y":
                return
        del dirs[index]
    except IndexError:
        LOG.error("Index is invalid")
    write_directory_list(path, dirs)


def add_global_skip(path, skips):
    """
    Add new skip to the config file. Use wildcards so fnmatch can match with filenames.
    :param path: Path to config file.
    :param skips: List or comma-separated string of items to skip.
    """
    LOG.debug("Adding global skip %s to list", skips)
    if isinstance(skips, list):
        skips = ",".join(skips)
    old_skips = get_config_key(path, SKIP_KEY)
    if old_skips:
        LOG.debug("Old global skips %s", old_skips)
        old_list = old_skips[0].split(",")
        for skip in skips.split(","):
            if not list_contains(skip, old_list):
                LOG.debug("Adding %s to %s", skip, old_list)
                old_list.append(skip)
        update_config_file(path, SKIP_KEY, ",".join(old_list))
    else:
        update_config_file(path, SKIP_KEY, skips)


def delete_global_skip(path, skips):
    """
    Remove skip from the config file.
    :param path: Path to config file.
    :param skips: List or comma-separated string of items to remove.
    """
    LOG.debug("Removing global skip %s from list", skips)
    if not isinstance(skips, list):
        skips = skips.split(",")
    old_skips = get_config_key(path, SKIP_KEY)
    if old_skips:
        old_list = old_skips[0].split(",")
        found = False
        for skip in skips:
            if skip in old_list:
                old_list.remove(skip)
                found = True
        if found:
            update_config_file(path, SKIP_KEY, ",".join(old_list))
            return

    LOG.warning("Global skip %s not found in list", skips)


def add_skip(path, skips, add_regex=None):
    """
    Add skips to config file.
    :param path: Path to config file.
    :param skips: List or comma-separated string of items to remove.
    :param add_regex: If true, add asterisks to make skip into a regex.
    """
    if len(skips) < 3:  # pragma: no cover
        print("Skip syntax: <src> <dest> <skip dir> {... <skip dir>}")
        print("Source and destination directories must be specified first")
        print("then one or more skip directories can be added.")
        print('Note: -s "*<string>*" is equivalent to -c "<string>"')
        return
    dirs = read_directory_list(path)
    src = skips[0]
    dest = skips[1]
    LOG.info("Adding skips to backup of %s to %s", src, dest)
    index = _make_paths_absolute_and_get_index(dirs, src, dest)
    if index is None:
        return

    line = dirs[index]
    for skip in skips[2:]:
        # if 'contains' option is used and regex hasn't already been added,
        # wrap skip string in any character regex
        if add_regex and skip[0] != "*" and skip[-1] != "*":
            skip = "*{0:s}*".format(skip)
        if skip in line[2:]:
            LOG.error("%s already added, aborting", skip)
            return
        if skip == line[0]:
            LOG.warning("%s would skip root dir, not added", skip)
        else:
            line.append(skip)
            LOG.info("  %s", skip)

    write_directory_list(path, dirs)


def perform_backup(directories, timestamp=None, adb=False):
    """
    Run backup of selected directories.
    :param directories: List of directories to backup.
    :param timestamp: Used for unit testing. If not given, the current time will be used.
    :param adb: If true, use adb for backup.
    """
    if len(directories) < 2:
        LOG.error("Not enough directories to backup")
        LOG.error(directories)
        return
    src = directories[0]
    dest = directories[1]
    skip = directories[2:] if len(directories) > 2 else None
    LOG.info("Backup of directory %s to %s%s", src, dest, " using adb" if adb else "")
    if skip is not None:
        LOG.info("  skipping directories that match %s", " or ".join(skip))
    # check dest exists before indexing
    if not os.path.exists(dest):
        LOG.warning("Destination path %s not found, creating directory", dest)
        make_directory(dest)
        if not os.path.exists(dest):
            # make directory failed
            return
    fi = FileIndex(src, skip, adb=adb)
    fi.gen_index()
    backup = Backup(dest, fi, latest_backup(dest), timestamp)
    backup.write_to_disk()


def search_backup(path, filename, files, folders, exact_match=True):
    """
    Look through all the backups in path for filename, returning any files or folders that match.
    :param path: Path to backup folder.
    :param filename: Name of file to search for.
    :param files: List of file names.
    :param folders: List of folder names.
    :param exact_match: If True, match the name exactly, if False, do a partial match.
    """
    LOG.debug("Searching %s (exact=%s)", path, exact_match)
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
                    LOG.debug("Hash %s changed, adding backup", last_hash)
                    files.append(last_backup)
                last_hash = this_hash
        last_backup = this_backup

        # also see if filename matches any of the folders in this backup
        if this_backup.contains_folder(filename, exact_match):
            LOG.debug("Folder found, adding backup to list")
            folders.append(this_backup)
    # check if oldest backup needs to be added
    if last_hash is not None:
        LOG.debug("Hash %s changed, adding backup", last_hash)
        files.append(last_backup)


def find_file_in_backup(dirlist, filename, index=None, restore_path=None):
    """
    Look through all previous backups to find files or folders to restore.
    :param dirlist: List of source/destination pairs to search through (taken from config file).
    :param filename: File or folder name to search for. Can be full path or just part of the name.
    :param index: Used for unit testing. When multiple versions of a file are available,
    automatically pick a specific backup. If not given, the user will be prompted for the version
    to restore.
    :param restore_path: An alternative location to restore to.
    """
    files = []
    folders = []
    searched = []

    # try a few times to find file, with less strict criteria on each pass
    for attempt in range(4):
        LOG.debug("Attempt %s", attempt)
        for dirs in dirlist:
            if 0 == attempt:
                # check if input matches a config entry
                if string_equals(dirs[0], filename):
                    LOG.debug("Restoring all backups from %s", dirs[0])
                    for zip_path in all_backups(dirs[1]):
                        read_backup(os.path.join(dirs[1], zip_path)).restore_folder(
                            filename, restore_path
                        )
                    return

            if 1 == attempt:
                # then look in all folders for exact string entered
                if string_contains(dirs[0], filename) or string_contains(filename, dirs[0]):
                    searched.append(dirs)
                    LOG.debug("String contains, looking in %s", dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 2 == attempt:
                # then look in remaining folders for exact string entered
                if dirs not in searched:
                    LOG.debug("Dirs not searched, looking in %s", dirs[1])
                    search_backup(dirs[1], filename, files, folders)

            if 3 == attempt:
                # then look in all folders again in case partial path given
                LOG.debug("Looking for partial match in %s", dirs[1])
                search_backup(dirs[1], filename, files, folders, exact_match=False)

        # found something, restore it and return
        if files:
            # select version to restore
            if len(files) > 1:
                LOG.info("Multiple versions of %s found:", filename)
                count = 1
                for backup in files:
                    LOG.info("[%s] %s", count, backup.get_tarpath())
                    count += 1
                if index is None:  # pragma: no cover
                    chosen = ""
                    try:
                        chosen = input(
                            "Please choose a version to restore (leave blank to cancel):"
                        )
                        if not chosen:
                            return  # user has cancelled restore
                        index = int(chosen) - 1
                        LOG.debug("index=%s", index)
                        # now check index is valid
                        if index < 0 or index >= len(files):
                            raise IndexError
                    except (TypeError, IndexError, ValueError):
                        LOG.error('"%s" is not a valid choice', chosen)
                        return
            else:
                LOG.debug("One version of %s found", filename)
                if index is not None:
                    LOG.warning("Ignoring index %s and defaulting to 0", index)
                index = 0
            try:
                files[index].restore_file(filename, restore_path)
            except IndexError:
                LOG.error("Index %s is not valid", index)
                return
        elif folders:
            # restore all folders, oldest first
            # (should have been discovered in date order)
            folders.reverse()
            for backup in folders:
                backup.restore_folder(filename, restore_path)

        if files or folders:
            LOG.debug("Files found, returning")
            return

    LOG.warning("%s not found", filename)


def perform_restore(dirlist, files=None, chosen_index=None, restore_path=None):
    """
    Restore files or folders.
    :param dirlist: List of source/destination pairs to search through (taken from config file).
    :param files: List of files to restore. Can be full path or just part of the name.
    :param chosen_index: Used for unit testing. When multiple versions of a file are available,
    automatically pick a specific backup. If not given, the user will be prompted for the version
    to restore.
    :param restore_path: Path to restore files and/or folders to, instead of original folder.
    """
    if not files:
        LOG.debug("Restoring all files")
        if chosen_index:
            LOG.warning("Restoring all files but index given, chosen index will be reset to 0")
        for dirs in dirlist:
            # restore each file present at time of last backup
            latest = latest_backup(dirs[1])
            for filename in latest.get_index().files():
                find_file_in_backup([dirs], filename, index=0, restore_path=restore_path)

            # check all folders are present (i.e. empty folders)
            for dirname in latest.get_index().dirs():
                if not os.path.exists(dirname):
                    make_directory(dirname)
    else:
        # check if first arg is an index
        match_index = re.match(r"#(\d+)", files[0])
        if match_index:
            try:
                # remove index from files arg
                files = files[1:]
                # reduce dirlist to chosen entry only
                list_index = int(match_index.group(1))
                dirlist = [dirlist[list_index - 1]]
            except (IndexError, TypeError):
                LOG.warning("Restore index not valid: %s", match_index.groups())
                return
        for filename in files:
            # restoring individual files/folders
            LOG.debug("Looking for %s", filename)
            find_file_in_backup(dirlist, filename, index=chosen_index, restore_path=restore_path)


def init(file_config):
    """
    Open the config file or create a new one if not found.
    :param file_config: Path to config file.
    """
    LOG.debug("Opening config file")
    try:
        if get_config_version(file_config):
            return
        LOG.debug("Version not found")
    except IOError:
        LOG.debug("Not found, creating new config")
    update_config_file(file_config, VERSION_KEY, version("backpy"))


def parse_args():  # pragma: no cover
    """Build arg parser"""
    parser = ArgumentParser(description="Command line backup utility.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", dest="verbose", help="Enable verbose logging."
    )
    parser.add_argument("--version", action="store_true", dest="show_version", help="Show version.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l",
        "--list",
        dest="list",
        action="store_true",
        required=False,
        help="List the all the directories currently in the config file, with index number.",
    )
    group.add_argument(
        "-a",
        "--add",
        metavar="path",
        nargs="+",
        dest="add_path",
        required=False,
        help="Adds the specified source directory to the backup index. The backups "
        "will be stored in the specified destination directory. If relative "
        "paths used, the current working directory will be added.",
    )
    group.add_argument(
        "-d",
        "--delete",
        metavar="path",
        nargs="+",
        dest="delete_path",
        required=False,
        help="Remove the specified source and destination directories from the "
        "backup.lst file. Can also specify directories by index (see list).",
    )
    group.add_argument(
        "-s",
        "--skip",
        dest="skip",
        metavar="string",
        nargs="+",
        required=False,
        help=r"Skips all files and directories that match the given fnmatch "
        r"expression, e.g. skip all subdirectories with <source dir>\*\*.",
    )
    group.add_argument(
        "-c",
        "--contains",
        dest="contains",
        metavar="string",
        nargs="+",
        required=False,
        help="Skips all directories that match the given fnmatch expression.",
    )
    group.add_argument(
        "-g",
        "--add-global-skip",
        dest="add_global_skip",
        metavar="string",
        nargs="+",
        required=False,
        help="Skip the given fnmatch expression(s) in all backups, e.g. *.jpg.",
    )
    group.add_argument(
        "-e",
        "--delete-global-skip",
        dest="delete_global_skip",
        metavar="string",
        nargs="+",
        required=False,
        help="Remove global skip(s) from the backup.lst file.",
    )
    group.add_argument(
        "-b",
        "--backup",
        action="store_true",
        dest="backup",
        help="Performs a backup for all paths specified in the backup.lst file.",
    )
    group.add_argument(
        "-r",
        "--restore",
        metavar="path",
        nargs="*",
        dest="restore",
        required=False,
        help="Restore selected files to their original folders. Can give full file "
        "path or just the file name. Leave blank to restore all. Using #n as "
        "first argument limits the search to just the config entry with the "
        "given index (see list).",
    )
    group.add_argument(
        "-t",
        "--temp-restore",
        metavar="path",
        nargs="+",
        dest="temp_restore",
        required=False,
        help="As restore, but with TEMP RESTORE DIR and BACKUP DIR paths given as "
        "the first two arguments, instead of read from the config file.",
    )
    group.add_argument(
        "-n",
        "--adb",
        "--android",
        nargs="+",
        dest="adb",
        metavar="path",
        required=False,
        help="Backs up the connected android device to the given folder. Defaults "
        "to copying from /sdcard/, but can optionally specify source folder as "
        "a second argument.",
    )
    return vars(parser.parse_args())


def run_backpy():  # pragma: no cover
    """Run backpy from commandline args."""
    args = parse_args()
    start = datetime.now()
    set_up_logging(2 if args["verbose"] else 1)
    init(CONFIG_FILE)
    backup_dirs = read_directory_list(CONFIG_FILE)
    if (args["backup"] or args["restore"] or args["adb"]) and not os.path.exists(TEMP_DIR):
        make_directory(TEMP_DIR)
    if args["show_version"]:
        LOG.info("Backpy version: %s", version("backpy"))
    elif args["list"]:
        show_directory_list(backup_dirs)
    elif args["add_path"]:
        new_args = handle_arg_spaces(args["add_path"])
        if len(new_args) > 1:
            add_directory(CONFIG_FILE, new_args[0], new_args[1])
        else:
            LOG.error("Two valid paths not given")
    elif args["delete_path"]:
        new_args = handle_arg_spaces(args["delete_path"])
        if len(new_args) > 1:
            delete_directory(CONFIG_FILE, new_args[0], new_args[1])
        else:
            try:
                index = int(new_args[0])
                dirs = read_directory_list(CONFIG_FILE)
                delete_directory_by_index(CONFIG_FILE, index - 1, dirs)
            except (ValueError, IndexError):
                LOG.error("Two valid paths not given or index is invalid")
    elif args["skip"]:
        add_skip(CONFIG_FILE, args["skip"])
    elif args["contains"]:
        add_skip(CONFIG_FILE, args["contains"], True)
    elif args["add_global_skip"]:
        add_global_skip(CONFIG_FILE, args["add_global_skip"])
    elif args["delete_global_skip"]:
        delete_global_skip(CONFIG_FILE, args["delete_global_skip"])
    elif args["backup"]:
        for directory in backup_dirs:
            print("")
            perform_backup(directory)
    elif args["adb"]:
        source = "/sdcard/"
        if len(args["adb"]) > 1:
            source = args["adb"][1]
        perform_backup([source, args["adb"][0]], adb=True)
    elif args["restore"] is not None:
        perform_restore(backup_dirs, args["restore"])
    elif args["temp_restore"] is not None:
        paths = args["temp_restore"]
        if len(paths) < 2:
            print(
                "Not enough arguments to perform temp restore."
                "Please specify source (location of existing backup)\n"
                "and destination (location to restore files to) and\n"
                "optionally, file(s) to be restored."
            )
        else:
            perform_restore([["", paths[1]]], paths[2:], restore_path=paths[0])
    else:
        print("Please specify a program option.\nInvoke with --help for futher information.")

    if args["backup"] or args["restore"] or args["adb"]:
        print("")
        LOG.info("Done. Elapsed time = %s", datetime.now() - start)


if __name__ == "__main__":
    run_backpy()
else:
    set_up_logging(0)  # set up default logging on import
