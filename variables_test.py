"""Tests for the variables module.
"""

import os
import requests
import unittest

#from testing.stub_requests import StubRequests
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient

# TODO(Will): Make these settings injected for test cases in a more general way.
os.environ['JOULIA_WEBSERVER_BREWHOUSE_ID'] = "1"
os.environ['JOULIA_WEBSERVER_HOST'] = "badhost"
os.environ['JOULIA_WEBSERVER_AUTHTOKEN'] = "badtoken"

import variables


class TestManagedVariable(unittest.TestCase):
    """Tests for the variables.ManagedVariable class.
    """
    def setUp(self):
        self.address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(self.address, auth_token=None)

    def test_unset_get_no_default(self):
        """Checks the case where the variable has no default and a get is
        attempted on it.
        """
        class TestClass(object):
            foo = variables.ManagedVariable("foo")
        instance = TestClass()

        with self.assertRaises(AttributeError):
            _ = instance.foo

    def test_unset_get_has_default(self):
        """Checks the case where the variable has a default and a get is
        attempted on it.
        """
        class TestClass(object):
            foo = variables.ManagedVariable("foo", default=10)
        instance = TestClass()

        self.assertEquals(instance.foo, 10)

    def test_set_and_get_one_instance(self):
        """Checks the simple case for a single ManagedVariable on a single
        instance of a class.
        """
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        instance = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.http_client, instance, recipe_instance)

        instance.foo = 1
        self.assertEquals(instance.foo, 1)

        instance.foo = 2
        self.assertEquals(instance.foo, 2)

    def test_set_and_get_two_instance(self):
        """Makes sure multiple instances of a class with a ManagedVariable do
        not have any coupling together.
        """
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        instance = TestClass()
        instance2 = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.http_client, instance, recipe_instance)

        # Edit instance2 then instance1
        instance2.foo = 3
        instance.foo = 1
        self.assertEquals(instance.foo, 1)
        self.assertEquals(instance2.foo, 3)

        # Edit instance1 then instance2
        instance.foo = 2
        instance2.foo = 4
        self.assertEquals(instance.foo, 2)
        self.assertEquals(instance2.foo, 4)

    def test_set_and_get_two_variables(self):
        """Makes sure multiple instances of a ManagedVariable in a single class
        do not have any coupling together.
        """
        class TestClass(object):
            foo = variables.ManagedVariable("foo")
            bar = variables.ManagedVariable("bar")

        instance = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.http_client, instance, recipe_instance)

        # Edit bar then foo
        instance.bar = 3
        instance.foo = 1
        self.assertEquals(instance.foo, 1)
        self.assertEquals(instance.bar, 3)

        # Edit foo then bar
        instance.foo = 2
        instance.bar = 4
        self.assertEquals(instance.foo, 2)
        self.assertEquals(instance.bar, 4)

    def test_get_class_object(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        TestClass()

        self.assertIsInstance(TestClass.foo, variables.ManagedVariable)

    def test_register(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        instance = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.http_client, instance, recipe_instance)

        self.assertEquals(TestClass.foo.clients[instance], self.http_client)
        self.assertIn(instance, TestClass.foo.registered)

    def test_identify(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        self.http_client.identifier = 11
        instance = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.http_client, instance, recipe_instance)

        TestClass.foo.identify(instance, recipe_instance)

        got = TestClass.foo.ids[instance]
        want = 11
        self.assertEquals(got, want)

# class TestWebsocketVariable(TestCase):
#     """Tests for the variables.WebsocketVariable class.
#     """
#     def setUp(self):
#         self.stub_requests = StubRequests()
#
#     def test_websocket_connect(self):
#         class TestClass(object):
#             foo = variables.WebsocketVariable("websocket_variable")


if __name__ == '__main__':
    unittest.main()
