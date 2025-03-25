# coding=utf-8
"""Module taken from OpenStudio-standards.

https://github.com/NREL/openstudio-standards/blob/master/
lib/openstudio-standards/prototypes/common/objects/Prototype.utilities.rb
"""
from __future__ import division

import re


def kw_per_ton_to_cop(kw_per_ton):
    """A helper method to convert from kW/ton to COP."""
    return 3.517 / kw_per_ton


def ems_friendly_name(name):
    """Converts existing string to ems friendly string."""
    # replace white space and special characters with underscore
    # \W is equivalent to [^a-zA-Z0-9_]
    new_name = re.sub('[^A-Za-z0-9]', '_', str(name))
    # prepend ems_ in case the name starts with a number
    new_name = 'ems_{}'.format(new_name)
    return new_name
