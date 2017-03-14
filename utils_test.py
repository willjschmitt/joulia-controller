"""Tests for the utils module."""

import unittest

from utils import exists_and_not_none
from utils import rgetattr
from utils import rsetattr


class TestRsetattr(unittest.TestCase):
    """Tests for rsetattr."""

    def test_set_on_same(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        foo = Foo()

        rsetattr(foo, "foo_var", 12)
        got = foo.foo_var
        self.assertEquals(got, 12)

    def test_set_on_related(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        class Bar(object):
            def __init__(self):
                self.bar_var = Foo()

        bar = Bar()

        rsetattr(bar, "bar_var__foo_var", 12)
        got = bar.bar_var.foo_var
        self.assertEquals(got, 12)

    def test_set_on_nested_related(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        class Bar(object):
            def __init__(self):
                self.bar_var = Foo()

        class Baz(object):
            def __init__(self):
                self.baz_var = Bar()

        baz = Baz()

        rsetattr(baz, "baz_var__bar_var__foo_var", 12)
        got = baz.baz_var.bar_var.foo_var
        self.assertEquals(got, 12)

    def test_set_doesnt_exist(self):
        class Foo(object):
            pass

        foo = Foo()

        with self.assertRaises(AttributeError):
            rsetattr(foo, "bar_var", 12)


class TestRgetattr(unittest.TestCase):
    """Tests for rgetattr."""

    def test_get_on_same(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        foo = Foo()

        rgetattr(foo, "foo_var")
        got = foo.foo_var
        self.assertEquals(got, 11)

    def test_get_on_related(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        class Bar(object):
            def __init__(self):
                self.bar_var = Foo()

        bar = Bar()

        rgetattr(bar, "bar_var__foo_var")
        got = bar.bar_var.foo_var
        self.assertEquals(got, 11)

    def test_get_on_nested_related(self):
        class Foo(object):
            def __init__(self):
                self.foo_var = 11

        class Bar(object):
            def __init__(self):
                self.bar_var = Foo()

        class Baz(object):
            def __init__(self):
                self.baz_var = Bar()

        baz = Baz()

        rgetattr(baz, "baz_var__bar_var__foo_var")
        got = baz.baz_var.bar_var.foo_var
        self.assertEquals(got, 11)

    def test_get_doesnt_exist(self):
        class Foo(object):
            pass

        foo = Foo()

        with self.assertRaises(AttributeError):
            rgetattr(foo, "bar_var")


class TestExistsAndNotNone(unittest.TestCase):
    """Tests for exists_and_not_none."""

    def test_does_not_exist(self):
        foo = {}
        self.assertFalse(exists_and_not_none(foo, "foo"))

    def test_exists_and_none(self):
        foo = {"foo": None}
        self.assertFalse(exists_and_not_none(foo, "foo"))

    def test_exists_and_not_none(self):
        foo = {"foo": 1}
        self.assertTrue(exists_and_not_none(foo, "foo"))
