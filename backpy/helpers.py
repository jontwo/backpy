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
from hashlib import md5
from shutil import rmtree

# Project imports
from logger import logger


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
            logger.warning('could not delete %s' % path)
        return

    if os.path.isdir(path):
        try:
            os.chmod(path, 0o777)
            rmtree(path)
        except OSError:
            logger.warning('could not delete %s' % path)


def make_directory(path):
    logger.debug('making directory {0}'.format(path))
    try:
        if os.path.pardir in path:
            os.mkdir(path)
        else:
            # best to use recursive make dir, but
            # only works if dest does not contain pardir (..)
            os.makedirs(path)
    except OSError:
        logger.error('could not create directory')


def string_equals(s1, s2):
    """
    Compare two strings, ignoring case for Windows
    :param s1: string to compare
    :param s2: string to compare
    :return: true if the strings are equal, false if not
    """
    if os.getenv("OS") == "Windows_NT":
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
    if os.getenv("OS") == "Windows_NT":
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
    if os.getenv("OS") == "Windows_NT":
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
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    return s1 in l2


def get_filename_index(s1, l2):
    """
    Get index for filename in list, ignoring case for Windows and ignoring path.
    Returns None if not found
    :param s1: name of file
    :param l2: list to search in
    :return: index number of file or None if not found
    """
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    try:
        return map(os.path.basename, l2).index(s1)
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
    if os.getenv("OS") == "Windows_NT":
        s1 = s1.lower()
        l2 = map(str.lower, l2)
    while l2 != map(os.path.dirname, l2):
        try:
            return map(os.path.basename, l2).index(s1)
        except ValueError:
            l2 = map(os.path.dirname, l2)
    return None


def handle_arg_spaces(old_args):
    """
    Some shells mess up the quoted input arguments, if so, reassemble them
    :param old_args: original input arguments
    :return: args list with quotes and spaces corrected
    """
    num_quotes = len(str(old_args)) - len(str(old_args).replace('\"', ''))
    if num_quotes % 2 != 0:
        logger.error('mismatched quotes in input argument: %s' % old_args)
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
        md5hash = md5(fullname)
        if size:
            md5hash.update(str(size))
        if ctime:
            md5hash.update(str(ctime))
    else:
        try:
            with open(fullname) as f:
                md5hash = md5(f.read())
        except (IOError, MemoryError):
            logger.warning('could not process file: %s' % fullname)

    return ''.join(['%x' % ord(h) for h in md5hash.digest()]) if md5hash else None
