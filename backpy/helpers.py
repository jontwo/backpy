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

import io
import logging
import os
import platform
import re
from hashlib import md5
from shutil import rmtree

from .logger import LOG_NAME

DEFAULT_KEY = 'default'
SKIP_KEY = 'global skips'
VERSION_KEY = 'backpy version'
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.backpy')
LOG = logging.getLogger(LOG_NAME)


def delete_temp_files(path):
    """
    Attempt to delete temporary files or folders in the given path.
    Just carry on if any can't be deleted.
    :param path: name of file or folder to delete
    """
    if os.path.isfile(path):
        # single file - delete it and return
        try:
            os.chmod(path, 0o777)
            os.unlink(path)
        except OSError:
            LOG.warning('could not delete %s', path)
        return

    if os.path.isdir(path):
        try:
            os.chmod(path, 0o777)
            rmtree(path)
        except OSError:
            LOG.warning('could not delete %s', path)


def make_directory(path):
    """
    Creates a directory
    :param path: path of directory to be created
    :raise OSError: if directory cannot be created
    """
    LOG.debug('making directory %s', path)
    try:
        if os.path.pardir in path:
            os.mkdir(path)
        else:
            # best to use recursive make dir, but
            # only works if dest does not contain pardir (..)
            os.makedirs(path)
    except OSError:
        LOG.error('could not create directory')


def string_equals(s1, s2):
    """
    Compare two strings, ignoring case for Windows
    :param s1: string to compare
    :param s2: string to compare
    :return: true if the strings are equal, false if not
    """
    if is_windows():
        s1 = s1.lower()
        s2 = s2.lower()
    return s1 == s2


def string_contains(s1, s2):
    """
    Check if one string contains another, ignoring case for Windows
    :param s1: string to search for
    :param s2: string to search in
    :return: true if s1 is found in s2, false if not
    """
    if not s1 or not s2:
        return False
    if is_windows():
        s1 = s1.lower()
        s2 = s2.lower()
    return s1 in s2


def string_startswith(s1, s2):
    """
    Check if one string starts with another, ignoring case for Windows
    :param s1: string to search for
    :param s2: string to search in
    :return: true if s2 starts with s1, false if not
    """
    if is_windows():
        s1 = s1.lower()
        s2 = s2.lower()
    return s2.startswith(s1)


def list_contains(s1, l2):
    """
    Check if list contains string, ignoring case for Windows
    :param s1: string to search for
    :param l2: list to search in
    :return: true if string is found in list, false if not
    """
    if is_windows():
        s1 = s1.lower()
        l2 = [item.lower() for item in l2]
    return s1 in l2


def get_filename_index(s1, l2):
    """
    Get index for filename in list, ignoring case for Windows and ignoring path.
    Returns None if not found
    :param s1: name of file
    :param l2: list to search in
    :return: index number of file or None if not found
    """
    if is_windows():
        s1 = s1.lower()
        l2 = [item.lower() for item in l2]
    try:
        return [os.path.basename(item) for item in l2].index(s1)
    except ValueError:
        return None


def get_folder_index(s1, l2):
    """
    Get index for folder in list, ignoring case for Windows.
    Returns longest path possible, or None if not found
    :param s1: name of folder
    :param l2: list to search in
    :return: index number of folder or None if not found
    """
    if is_windows():
        s1 = s1.lower()
        l2 = [item.lower() for item in l2]
    while l2 != [os.path.dirname(item) for item in l2]:
        try:
            return [os.path.basename(item) for item in l2].index(s1)
        except ValueError:
            l2 = [os.path.dirname(item) for item in l2]
    return None


def handle_arg_spaces(old_args):
    """
    Some shells mess up the quoted input arguments, if so, reassemble them
    :param old_args: original input arguments
    :return: args list with quotes and spaces corrected
    """
    num_quotes = len(str(old_args)) - len(str(old_args).replace('\"', ''))
    if num_quotes % 2 != 0:
        LOG.error('mismatched quotes in input argument: %s', old_args)
    elif num_quotes != 0:
        in_quote = False
        rebuilt_args = []
        quoted_arg = ''
        for arg in old_args:
            if in_quote:
                if arg[-1] == '\"':
                    # has closing quote, finish rebuilding
                    quoted_arg = '%s %s' % (quoted_arg, arg[:-1])
                    rebuilt_args.append(quoted_arg)
                    in_quote = False
                    quoted_arg = ''
                else:
                    # keep rebuilding
                    quoted_arg = '%s %s' % (quoted_arg, arg)
            else:
                if arg[0] == '\"':
                    # has opening quote, start rebuilding
                    quoted_arg = arg[1:]
                    in_quote = True
                else:
                    # just add without changing
                    rebuilt_args.append(arg)
        return rebuilt_args
    # no quotes, just return the original list
    return old_args


def get_file_hash(fullname, size=None, ctime=None):
    """
    Return a string representing the md5 hash of the given file.
    Use size and/or ctime args if file is on a phone and can't be read.
    :param fullname: full path of file
    :param size: file size (optional)
    :param ctime: file create time (optional)
    :return: hex string hash of file
    """
    md5hash = None
    if size or ctime:
        md5hash = md5(fullname.encode('latin1'))
        if size:
            md5hash.update(str(size).encode('latin1'))
        if ctime:
            md5hash.update(str(ctime).encode('latin1'))
    else:
        try:
            with io.open(fullname, encoding='latin1') as f:
                md5hash = md5(f.read().encode('latin1', errors='ignore'))
        except (IOError, MemoryError):
            LOG.warning('could not process file: %s', fullname)

    return md5hash.hexdigest() if md5hash else None


def get_config_version(path):
    """
    Get the version from the current config file.
    :param path: path of config file
    :return: version string
    """
    version = get_config_key(path, VERSION_KEY)
    if version:
        return version[0]
    return 0


def read_config_file(path):
    """
    Read a backpy config file (.backpy, .index, etc.) and return as a dictionary
    with a key for each section. Entries without a section header (i.e. old config files)
    are returned under the Default key
    :param path: path of config file
    :return: dict of file contents
    """
    this_key = 'default'
    items = {this_key: []}
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f.readlines():
                header = re.match(r'\[(.*)]', line.strip())
                if header:
                    header_text = header.group(1)
                    if '=' in header_text:
                        # handle parameters
                        param, val = header_text.split('=')
                        items[param] = val
                    else:
                        this_key = header_text
                        items[this_key] = []
                    continue
                items[this_key].append(line.strip())

    return items


def write_config_file(path, values):
    """
    Write a dictionary of config values to a file
    :param path: path of config file
    :param values: dictionary of key/value pairs to write
    """
    LOG.debug('writing values to config: %s', values)
    try:
        with open(path, "w+") as fp:
            for k, v in values.items():
                fp.write('[{}]\n'.format(k))
                for item in v:
                    fp.write('{}\n'.format(item))
    except IOError:
        LOG.warning('could not write to config file %s', path)


def update_config_file(path, key, val, overwrite=True):
    """
    Write a single key/value pair to a config file, leaving the other keys unchanged
    :param path: path of config file
    :param key: key to write to
    :param val: value to write, as a list
    :param overwrite: True to replace the existing value, False to append the new value
    """
    LOG.debug('updating config key %s', key)
    config = read_config_file(path)
    if not isinstance(val, list):
        val = [val]
    if overwrite:
        config[key] = val
    else:
        old_val = config.get(key, [])
        for item in val:
            if item not in old_val:
                old_val.append(item)
                config[key] = old_val
    write_config_file(path, config)


def get_config_key(path, key):
    """
    Read a config file and return the values under one key
    :param path: path of config file
    :param key: key to read
    :return: values under the key or an empty list
    """
    config = read_config_file(path)
    return config.get(key, [])


def is_osx():
    """Check current operating system is OSX"""
    return platform.system() == 'Darwin'


def is_windows():
    """Check current operating system is Windows"""
    return platform.system() == 'Windows'
