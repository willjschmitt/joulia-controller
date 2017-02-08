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
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


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


GPIO_MOCK_API_ACTIVE = 'gpio_mock' in dir(gpiocrust)
