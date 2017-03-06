"""Tests for the variables module.
"""

import os
import json
import requests

from unittest import TestCase

# TODO(Will): Make these settings injected for test cases in a more general way.
os.environ['JOULIA_WEBSERVER_BREWHOUSE_ID'] = "1"
os.environ['JOULIA_WEBSERVER_HOST'] = "badhost"
os.environ['JOULIA_WEBSERVER_AUTHTOKEN'] = "badtoken"

import variables

class TestManagedVariable(TestCase):
    """Tests for the variables.ManagedVariable class.
    """
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
        TestClass.foo.register(instance)

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
        TestClass.foo.register(instance)

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
        TestClass.foo.register(instance)

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

        instance = TestClass()

        self.assertIsInstance(TestClass.foo, variables.ManagedVariable)

    def test_register(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        instance = TestClass()
        TestClass.foo.register(instance)

        self.assertIn(instance, TestClass.foo.registered)

    def test_subscribe(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")

        instance = TestClass()
        TestClass.foo.subscribe(instance)

        self.assertIn(instance, TestClass.foo.subscribed)

    def test_post_server_not_there(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")
        instance = TestClass()
        TestClass.foo.register(instance)

        # Inject requests mock service
        requests_service = StubRequests()
        requests_service.server_there = False
        TestClass.foo._requests_service = requests_service

        with self.assertRaises(requests.exceptions.ConnectionError):
            TestClass.foo.post(instance, "fake.url/nowhere")

    def test_post_ok(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")
        instance = TestClass()
        TestClass.foo.register(instance)

        # Inject requests mock service
        requests_service = StubRequests()
        requests_service.response_string = '{"foo":1}'
        TestClass.foo._requests_service = requests_service

        response = TestClass.foo.post(instance, "fake.url/nowhere")

        self.assertEquals(response.json(), {"foo": 1})

    def test_post_server_error(self):
        class TestClass(object):
            foo = variables.ManagedVariable("foo")
        instance = TestClass()
        TestClass.foo.register(instance)

        # Inject requests mock service
        requests_service = StubRequests()
        requests_service.status_code = 500
        requests_service.reason = "Internal server error."
        TestClass.foo._requests_service = requests_service

        with self.assertRaises(requests.exceptions.HTTPError):
            TestClass.foo.post(instance, "fake.url/nowhere")


# class TestWebsocketVariable(TestCase):
#     """Tests for the variables.WebsocketVariable class.
#     """
#     def setUp(self):
#         self.stub_requests = StubRequests()
#
#     def test_websocket_connect(self):
#         class TestClass(object):
#             foo = variables.WebsocketVariable("websocket_variable")
