"""Tests for the variables module.
"""

import json
import unittest

from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient
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

        self.http_client.identifier = 11
        TestClass.foo.identify(instance, recipe_instance)

        got = TestClass.foo.ids[instance]
        want = 11
        self.assertEquals(got, want)


class TestWebsocketVariable(unittest.TestCase):
    """Tests for WebsocketVariable."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.ws_address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)
        self.ws_client = StubJouliaWebsocketClient(
            self.ws_address, self.http_client)

    def test_init(self):
        variables.WebsocketVariable("websocket_variable")

    def test_register_ws_client(self):
        class TestClass(object):
            foo = variables.StreamingVariable("foo")

        instance = TestClass()
        recipe_instance = 0
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

    def test_register_http_client_fails(self):
        class TestClass(object):
            foo = variables.StreamingVariable("foo")

        instance = TestClass()
        recipe_instance = 0
        with self.assertRaises(AssertionError):
            TestClass.foo.register(self.http_client, instance, recipe_instance)


class TestStreamingVariable(unittest.TestCase):
    """Tests for StreamingVariable."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.ws_address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)
        self.ws_client = StubJouliaWebsocketClient(
            self.ws_address, self.http_client)

    def test_set(self):
        class TestClass(object):
            foo = variables.StreamingVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.ws_client.http_client.identifier = 3
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        instance.foo = 2
        self.assertEquals(instance.foo, 2)

        date_regexp = r'\d{4}[-/]\d{2}[-/]\d{2}'
        time_regexp = r'\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}'
        datetime_regexp = "{}T{}".format(date_regexp, time_regexp)

        got = self.ws_client.websocket.written_messages[0]
        parsed = json.loads(got)
        self.assertRegexpMatches(parsed['time'], datetime_regexp)
        self.assertEquals(parsed['recipe_instance'], recipe_instance)
        self.assertEquals(parsed['value'], 2)
        self.assertEquals(parsed['sensor'], 3)


class TestSubscribableVariable(unittest.TestCase):
    """Tests for SubscribableVariable."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.ws_address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)
        self.ws_client = StubJouliaWebsocketClient(
            self.ws_address, self.http_client)

    def test_register(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.ws_client.http_client.identifier = 3
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertIn(TestClass.foo.on_message, self.ws_client.callbacks)

    def test_subscribe(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        sensor_id = 11
        self.http_client.identifier = sensor_id

        # Calls _subscribe
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertIn((sensor_id, "value", recipe_instance),
                      TestClass.foo.subscribers)
        got = TestClass.foo.subscribers[(sensor_id, "value", recipe_instance)]
        want = {"instance": instance}
        self.assertEquals(got, want)

    def test_on_message_nothing_set(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        message = '{"sensor":11,"recipe_instance":1,"value":2}'
        TestClass.foo.on_message(message)

        self.assertEquals(instance.foo, 2)

    def test_on_message_int_set(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        instance.foo = 3

        message = '{"sensor":11,"recipe_instance":1,"value":2.0}'
        TestClass.foo.on_message(message)

        self.assertIsInstance(instance.foo, int)
        self.assertEquals(instance.foo, 2)

    def test_on_message_bool_set(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        instance.foo = True

        message = '{"sensor":11,"recipe_instance":1,"value":0}'
        TestClass.foo.on_message(message)

        self.assertIsInstance(instance.foo, bool)
        self.assertEquals(instance.foo, False)

    def test_on_message_calls_callback(self):
        class TestClass(object):
            foo = variables.SubscribableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        counters = {"bar": 0}

        def bar(self):
            counters['bar'] += 1

        TestClass.foo.register(self.ws_client, instance, recipe_instance,
                               callback=bar)

        message = '{"sensor":11,"recipe_instance":1,"value":0}'
        TestClass.foo.on_message(message)

        self.assertEquals(counters["bar"], 1)


class TestOverridableVariable(unittest.TestCase):
    """Tests for OverridableVariable."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.ws_address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)
        self.ws_client = StubJouliaWebsocketClient(
            self.ws_address, self.http_client)

    def test_register(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        sensor_id = 3
        self.ws_client.http_client.identifier = sensor_id
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertIn((sensor_id, "value", recipe_instance),
                      TestClass.foo.subscribers)
        self.assertIn((sensor_id, "override", recipe_instance),
                      TestClass.foo.subscribers)

    def test_set_not_overridden(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.ws_client.http_client.identifier = 3
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        instance.foo = 2
        self.assertEquals(instance.foo, 2)

        date_regexp = r'\d{4}[-/]\d{2}[-/]\d{2}'
        time_regexp = r'\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}'
        datetime_regexp = "{}T{}".format(date_regexp, time_regexp)

        # First two messages are for subscribing value and override. Third is
        # the actual sending of a new value
        self.assertEquals(len(self.ws_client.websocket.written_messages), 3)
        got = self.ws_client.websocket.written_messages[2]
        parsed = json.loads(got)
        self.assertRegexpMatches(parsed['time'], datetime_regexp)
        self.assertEquals(parsed['recipe_instance'], recipe_instance)
        self.assertEquals(parsed['value'], 2)
        self.assertEquals(parsed['sensor'], 3)

    def test_set_is_overridden(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foob", default=2)

        instance = TestClass()
        recipe_instance = 1
        self.ws_client.http_client.identifier = 3
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        TestClass.foo.overridden[instance] = True

        instance.foo = 22
        self.assertEquals(instance.foo, 2)

        # First two messages are for subscribing value and override. Third is
        # the actual sending of a new value, which we shouldn't see, since this
        # is overridden.
        self.assertEquals(len(self.ws_client.websocket.written_messages), 2)
        for message in self.ws_client.websocket.written_messages:
            parsed = json.loads(message)
            self.assertIn("subscribe", parsed)
            self.assertTrue(parsed["subscribe"])

    def test_on_message_override(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertFalse(TestClass.foo.overridden[instance])
        message = ('{"sensor":11,"recipe_instance":1,"value":1,'
                   '"variable_type":"override"}')
        TestClass.foo.on_message(message)
        self.assertTrue(TestClass.foo.overridden[instance])

    def test_on_message(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertFalse(TestClass.foo.overridden[instance])
        message = '{"sensor":11,"recipe_instance":1,"value":2}'
        TestClass.foo.on_message(message)
        self.assertFalse(TestClass.foo.overridden[instance])
        self.assertEquals(instance.foo, 2)

    def test_on_message_value(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertFalse(TestClass.foo.overridden[instance])
        message = ('{"sensor":11,"recipe_instance":1,"value":2,'
                   '"variable_type":"value"}')
        TestClass.foo.on_message(message)
        self.assertFalse(TestClass.foo.overridden[instance])
        self.assertEquals(instance.foo, 2)


class TestBidirectionalVariable(unittest.TestCase):
    """Tests for BidirectionalVariable."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.ws_address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)
        self.ws_client = StubJouliaWebsocketClient(
            self.ws_address, self.http_client)

    def test_register(self):
        class TestClass(object):
            foo = variables.OverridableVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        sensor_id = 3
        self.ws_client.http_client.identifier = sensor_id
        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        self.assertIn((sensor_id, "value", recipe_instance),
                      TestClass.foo.subscribers)
        self.assertIn((sensor_id, "override", recipe_instance),
                      TestClass.foo.subscribers)

    def test_on_message_override(self):
        class TestClass(object):
            foo = variables.BidirectionalVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        message = ('{"sensor":11,"recipe_instance":1,"value":1,'
                   '"variable_type":"override"}')
        TestClass.foo.on_message(message)

    def test_on_message(self):
        class TestClass(object):
            foo = variables.BidirectionalVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        message = '{"sensor":11,"recipe_instance":1,"value":2}'
        TestClass.foo.on_message(message)
        self.assertEquals(instance.foo, 2)

    def test_on_message_value(self):
        class TestClass(object):
            foo = variables.BidirectionalVariable("foo")

        instance = TestClass()
        recipe_instance = 1
        self.http_client.identifier = 11

        TestClass.foo.register(self.ws_client, instance, recipe_instance)

        message = ('{"sensor":11,"recipe_instance":1,"value":2}')
        TestClass.foo.on_message(message)
        self.assertEquals(instance.foo, 2)


class TestDataStreamer(unittest.TestCase):
    """Tests for DataStreamer."""

    def setUp(self):
        self.http_address = "http://fakehost"
        self.http_client = StubJouliaHTTPClient(
            self.http_address, auth_token=None)

    def test_start_stop(self):
        class TestClass(object):
            foo = 1
        instance = TestClass()
        recipe_instance = 0
        streamer = variables.DataStreamer(
            self.http_client, instance, recipe_instance, 1)

        streamer.start()
        streamer.stop()

    def test_register(self):
        class TestClass(object):
            foo = 1
        instance = TestClass()
        recipe_instance = 0
        self.http_client.identifier = 11
        streamer = variables.DataStreamer(
            self.http_client, instance, recipe_instance, 1)

        streamer.register("foo", "bar")

        self.assertEquals(streamer.attribute_to_name["foo"], "bar")
        self.assertEquals(streamer.ids["foo"], 11)
        self.assertEquals(streamer.id_to_attribute[11], "foo")

    def test_register_no_name(self):
        class TestClass(object):
            foo = 1
        instance = TestClass()
        recipe_instance = 0
        self.http_client.identifier = 11
        streamer = variables.DataStreamer(
            self.http_client, instance, recipe_instance, 1)

        streamer.register("foo")

        self.assertEquals(streamer.attribute_to_name["foo"], "foo")
        self.assertEquals(streamer.ids["foo"], 11)
        self.assertEquals(streamer.id_to_attribute[11], "foo")

    def test_register_double_register_fails(self):
        class TestClass(object):
            foo = 1
        instance = TestClass()
        recipe_instance = 0
        self.http_client.identifier = 11
        streamer = variables.DataStreamer(
            self.http_client, instance, recipe_instance, 1)

        streamer.register("foo")

        self.http_client.identifier = 11
        with self.assertRaises(AttributeError):
            streamer.register("foo")

    def test_post_data(self):
        class TestClass(object):
            foo = 1
            bar = 2
        instance = TestClass()
        recipe_instance = 0
        streamer = variables.DataStreamer(
            self.http_client, instance, recipe_instance, 1)

        self.http_client.identifier = 11
        streamer.register("foo")

        self.http_client.identifier = 12
        streamer.register("bar")

        streamer.post_data()

        # Enforces order of updates, which is not guaranteed, since the
        # production code iterates over a dict, which does not guarantee order.
        updates = sorted(self.http_client.update_sensor_value_posts,
                         key=lambda update: update['sensor'])
        got = updates[0]
        want = {"recipe_instance": recipe_instance,
                "value": 1,
                "sensor": 11}
        self.assertEquals(got, want)

        got = updates[1]
        want = {"recipe_instance": recipe_instance,
                "value": 2,
                "sensor": 12}
        self.assertEquals(got, want)
