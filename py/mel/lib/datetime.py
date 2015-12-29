"""Utilities for working with datetime."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import os


def guess_datetime_from_path(path):
    """Return None if no date could be guessed, datetime otherwise.

    Usage examples:

        >>> guess_datetime_from_path('inbox/Photo 05-01-2015 23 25 40.jpg')
        datetime.datetime(2015, 1, 5, 23, 25, 40)

        >>> guess_datetime_from_path('blah')

    :path: path string to be converted
    :returns: datetime.date if successful, None otherwise

    """
    # TODO: try the file date if unable to determine from name
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]
    return guess_datetime_from_string(name)


def guess_datetime_from_string(datetime_str):
    """Return None if no datetime could be guessed, datetime otherwise.

    Usage examples:

        >>> guess_datetime_from_string('Photo 05-01-2015 23 25 40')
        datetime.datetime(2015, 1, 5, 23, 25, 40)

        >>> guess_datetime_from_string('blah')

    :datetime_str: string to be converted
    :returns: datetime.datetime if successful, None otherwise

    """
    try:
        return datetime.datetime.strptime(
            datetime_str, 'Photo %d-%m-%Y %H %M %S')
    except ValueError:
        return None


def make_now_datetime_string():
    return make_datetime_string(datetime.utcnow())


def make_datetime_string(datetime_):
    return datetime_.strftime("%Y%m%dT%H%M%S")
