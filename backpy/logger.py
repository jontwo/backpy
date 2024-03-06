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
import logging.handlers
import os
import sys

LOG_NAME = 'backpy'
LOG_FILE = os.path.join(os.path.expanduser('~'), 'backpy.log')
_logger = logging.getLogger(LOG_NAME)


class SometimesRotatingFileHandler(logging.handlers.RotatingFileHandler):  # pragma: no cover
    """Custom class to handle windows file locks sometimes preventing file rollover.
    If it does, just carry on and hope the lock will be released before the log file
    fills up the drive..."""
    def doRollover(self):
        """Try and rollover log, do not raise if it fails."""
        try:
            super(SometimesRotatingFileHandler, self).doRollover()
        except OSError:
            pass


class SpecialFormatter(logging.Formatter):
    """Override the Python formatter to add custom logging."""

    FORMATS = {
        logging.DEBUG: "DEBUG: %(lineno)d: %(message)s",
        logging.INFO: "%(message)s",
        'DEFAULT': "%(levelname)s: %(message)s"
    }

    def format(self, record):  # noqa: A003,D102
        self._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        return super().format(record)


def set_log_path(log_path):  # pragma: no cover
    """Sets the log path module variable."""
    global LOG_FILE
    LOG_FILE = log_path


def set_up_logging(level=1):
    """Remove any existing log handlers and add the required handlers."""
    for h in list(_logger.handlers):
        _logger.removeHandler(h)

    _logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(SpecialFormatter())
    sh.setLevel(logging.INFO)
    if 2 == level:  # pragma: no cover
        sh.setLevel(logging.DEBUG)
    # kill console output (i.e. during unit tests)
    if 0 != level:
        _logger.addHandler(sh)
    fh = SometimesRotatingFileHandler(LOG_FILE, maxBytes=1000000, backupCount=3)
    fh.setLevel(logging.DEBUG)
    ff = logging.Formatter('%(asctime)s: %(levelname)s: %(funcName)s: %(message)s')
    fh.setFormatter(ff)
    _logger.addHandler(fh)
