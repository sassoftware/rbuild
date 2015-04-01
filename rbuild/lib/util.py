#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Generic utility functions that can be used by rbuild or rbuild plugins
"""

from datetime import datetime

from dateutil import parser as dtparser
from dateutil import tz


def convertTime(string):
    """Convert a time string to something human readable, and in local time

    If the string is unparsable, we simply return it unchanged

    :param str string: string representation of time
    """
    try:
        d = dtparser.parse(string)
    except ValueError:
        try:
            d = datetime.fromtimestamp(float(string))
        except ValueError:
            return string

    d.replace(tzinfo=tz.tzlocal())
    return datetime.strftime(d, "%Y/%m/%d %H:%M:%S")
