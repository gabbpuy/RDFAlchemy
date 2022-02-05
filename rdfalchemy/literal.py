# encoding: utf-8
"""
Literal.py

Created by Philip Cooper on 2008-02-09.
Copyright (c) 2008 Openvest. All rights reserved.
"""
import datetime
import re

from rdflib import Literal
from rdflib.term import bind as bind_literal
from rdfalchemy.namespaces import XSD

__all__ = ['Literal']


###############################################################################
# Default behavior returns untyped literals as literals
# this brings untyped literals back as unicode strings
bind_literal(None, str)

###############################################################################
# Default behavior returns string literals as literals
# this brings  string literals back as unicode strings
bind_literal(XSD.string, str)

###############################################################################
# Let's make toPython return a datetime if the literal has fractional seconds
# Note: dateparser adapted from http://www.mnot.net/python/isodate.py
# modified to: handle fractional seconds beyond tenths
#              and to allow pseudo iso i.e. "2001-12-15 22:43:46"
#                                        vs "2001-12-15T22:43:46"


date_parser = re.compile(r"""^
    (?P<year>\d{4})
    (?:-
        (?P<month>\d{1,2})
        (?:-
            (?P<day>\d{1,2})
            (?:[T ]
                (?P<hour>\d{1,2})
                :
                (?P<minute>\d{1,2})
                (?::
                    (?P<second>\d{1,2})
                    (?P<dec_second>\.\d+)?
                )?
                (?:Z|(?:
                        (?P<tz_sign>[+-])
                        (?P<tz_hour>\d{1,2})
                        :?
                        (?P<tz_min>\d{2,2})
                     )
                )?
            )?
        )?
    )?
$""", re.VERBOSE)


def str_to_datetime(s):
    """
    parse a string and return a datetime object.
    """
    assert isinstance(s, str)
    r = date_parser.search(s)
    try:
        a = r.groupdict('0')
    except:
        raise ValueError('invalid date string format')

    dt = datetime.datetime(int(a['year']),
                           int(a['month']) or 1,
                           int(a['day']) or 1,
                           # If not given these will default to 00:00:00.0
                           int(a['hour']),
                           int(a['minute']),
                           int(a['second']),
                           # Convert into microseconds
                           int(float(a['dec_second']) * 1000000),
                           )
    tz_hours_offset = int(a['tz_hour'])
    tz_mins_offset = int(a['tz_min'])
    if a.get('tz_sign', '+') == "-":
        return dt + datetime.timedelta(hours=tz_hours_offset,
                                       minutes=tz_mins_offset)
    else:
        return dt - datetime.timedelta(hours=tz_hours_offset,
                                       minutes=tz_mins_offset)


bind_literal(XSD.dateTime, str_to_datetime)
