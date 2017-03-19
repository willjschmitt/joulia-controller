"""Utility functions for ``joulia-controller`` project as well as data
streaming enabled property-like functions that handle the sharing and
accepting of data with and from a ``joulia-webserver`` instance.
"""
import functools
import logging

import gpiocrust

LOGGER = logging.getLogger(__name__)


def rsetattr(obj, attr, val):
    """Sets nested attribute of child elements separating attribute path
    using a double underscore.

    Example: `attr` "foo__bar" sets the value at `obj.foo.bar`

    Args:
        obj: The object to set the value on.
        attr: The attribute path with dunderscores separating attribute paths
        val: value to set
    """
    pre, _, post = attr.rpartition('__')

    leaf_obj = rgetattr(obj, pre) if pre else obj

    if not hasattr(leaf_obj, post):
        raise AttributeError(
            "{}.{} has no attribute {} on it, and rsetattr does not initialize"
            "values.".format(obj, pre, post))

    return setattr(leaf_obj, post, val)


def rgetattr(obj, attr):
    """Gets nested attribute of child elements separating attribute path
    using a double underscore.

    Example: `attr` "foo__bar" gets the value at `obj.foo.bar`

    Args:
        obj: The object to set the value on.
        attr: The attribute path with dunderscores separating attribute paths

    Returns: value at the attribute
    """
    return functools.reduce(getattr, [obj] + attr.split('__'))


def exists_and_not_none(obj, key):
    """Checks if `key` is in `obj` and if it is not None. Returns boolean
    indicating the key exists and is not None.
    """
    return key in obj and obj[key] is not None


def power_to_temperature_rate(power, volume):
    """Converts power (in Watts) and volume of water (in gallons) into
    temperature change rate (in degF/second).
    """
    volume *= 3.79  # L
    density_water = 1000.0  # grams/L
    mass = volume * density_water  # grams
    specific_heat_water = 4.184  # J/(degC * grams)
    specific_heat = mass * specific_heat_water  # J/degC
    specific_heat_fahrenheit = specific_heat * (5.0 / 9.0)  # J/degF
    return power / specific_heat_fahrenheit  # degF/second


GPIO_MOCK_API_ACTIVE = 'gpio_mock' in dir(gpiocrust)
