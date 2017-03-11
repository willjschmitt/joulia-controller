"""Tests for joulia_webserver_client module."""

import json
import unittest

from joulia_webserver_client import JouliaHTTPClient
from joulia_webserver_client import JouliaWebsocketClient
from joulia_webserver_client import JouliaWebserverClientBase
from testing.stub_requests import StubRequests
from testing.stub_websocket import stub_websocket_connect
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient


class JouliaHTTPClientTest(JouliaHTTPClient):
    """Subclass to override and stub out the requests module."""
    def __init__(self, address, auth_token=None):
        # Inject dependencies
        self._requests_service = StubRequests()

        super(JouliaHTTPClientTest, self).__init__(
            address, auth_token=auth_token)


class JouliaWebsocketClientTest(JouliaWebsocketClient):
    """Subclass to override and stub out the websocket module."""
    def __init__(self,  address, http_client, auth_token=None):
        # Inject dependencies
        self._websocket_connect = stub_websocket_connect

        super(JouliaWebsocketClientTest, self).__init__(
            address, http_client, auth_token=auth_token)


class TestJouliaWebserverClientBase(unittest.TestCase):
    """Tests JouliaWebserverClientBase."""

    def setUp(self):
        self.address = "http://fakehost"
        self.client = JouliaWebserverClientBase(self.address)

    def test_identify(self):
        sensor_name = "foo"
        recipe_instance = 0
        with self.assertRaises(NotImplementedError):
            self.client.identify(sensor_name, recipe_instance)

    def test_update_sensor_value(self):
        recipe_instance = 0
        value = 0
        sensor = 0
        with self.assertRaises(NotImplementedError):
            self.client.update_sensor_value(recipe_instance, value, sensor)

    def test_clean_value_none(self):
        value = None
        got = self.client.clean_value(value)
        want = 0
        self.assertEquals(got, want)

    def test_clean_value_true(self):
        value = True
        got = self.client.clean_value(value)
        want = 1
        self.assertEquals(got, want)

    def test_clean_value_false(self):
        value = False
        got = self.client.clean_value(value)
        want = 0
        self.assertEquals(got, want)

    def test_clean_value_int(self):
        value = 11
        got = self.client.clean_value(value)
        want = 11
        self.assertEquals(got, want)

    def test_clean_value_float(self):
        value = 13.2
        got = self.client.clean_value(value)
        want = 13.2
        self.assertAlmostEquals(got, want, 6)


class TestJouliaHttpClient(unittest.TestCase):
    """Tests JouliaHttpClient."""

    def setUp(self):
        self.address = "http://fakehost"
        self.client = JouliaHTTPClientTest(self.address, auth_token=None)

    def test_auth_headers_with_token(self):
        client = JouliaHTTPClientTest(self.address, auth_token="faketoken")

        got = client._authorization_headers()
        want = {'Authorization': 'Token faketoken'}
        self.assertEqual(got, want)

    def test_auth_headers_without_token(self):
        client = JouliaHTTPClientTest(self.address, auth_token=None)

        got = client._authorization_headers()
        want = {}
        self.assertEqual(got, want)

    def test_post(self):
        self.client._requests_service.response_string = '{"foo":"bar"}'
        response = self.client._post("fakeurl", data={'baz': 1})
        self.assertEqual(response.json(), {"foo": "bar"})

    def test_identify_url(self):
        got = self.client._identify_url
        want = "http://fakehost/live/timeseries/identify/"
        self.assertEqual(got, want)

    def test_identify(self):
        self.client._requests_service.response_string = '{"sensor":11}'
        sensor_name = "fake_sensor"
        recipe_instance = 1
        got = self.client.identify(sensor_name, recipe_instance)
        want = 11
        self.assertEqual(got, want)


class TestJouliaWebsocketClient(unittest.TestCase):
    """Tests JouliaWebsocketClient."""
    # TODO(will): Add test for creating a client where the delay on the
    # websocket connecting is greater than 0.

    def setUp(self):
        self.address = "ws://fakehost"
        self.http_client = StubJouliaHTTPClient(self.address, auth_token=None)
        self.client = JouliaWebsocketClientTest(
            self.address, self.http_client, auth_token=None)

    def test_write_message(self):
        self.client.write_message("foo")
        got = self.client.websocket.written_messages
        want = ["foo"]
        self.assertEquals(got, want)

    def test_update_sensor_value_correct_written_message(self):
        recipe_instance = 1
        value = 2
        sensor = 3
        self.client.update_sensor_value(recipe_instance, value, sensor)

        date_regexp = r'\d{4}[-/]\d{2}[-/]\d{2}'
        time_regexp = r'\d{2}:\d{2}:\d{2}.\d{6}\+\d{2}:\d{2}'
        datetime_regexp = "{}T{}".format(date_regexp, time_regexp)

        got = self.client.websocket.written_messages[0]
        parsed = json.loads(got)
        self.assertRegexpMatches(parsed['time'], datetime_regexp)
        self.assertEquals(parsed['recipe_instance'], recipe_instance)
        self.assertEquals(parsed['value'], 2)
        self.assertEquals(parsed['sensor'], 3)

    def test_identify(self):
        self.client.http_client.identifier = 11
        sensor_name = "fake_sensor"
        recipe_instance = 1
        got = self.client.identify(sensor_name, recipe_instance)
        want = 11
        self.assertEqual(got, want)

    def test_subscribe(self):
        recipe_instance = 1
        sensor = 3
        self.client.subscribe(recipe_instance,sensor)

        got = self.client.websocket.written_messages[0]
        parsed = json.loads(got)
        self.assertEquals(parsed['recipe_instance'], recipe_instance)
        self.assertEquals(parsed['sensor'], 3)
        self.assertEquals(parsed['subscribe'], True)

    def test_register_callback(self):
        def foo(response):
            pass

        self.client.register_callback(foo)

        self.assertIn(foo, self.client.callbacks)

    def test_on_message_callback(self):
        counters = {"foo": 0}

        def foo(response):
            counters["foo"] += 1

        self.client.register_callback(foo)

        self.client.on_message("")

        self.assertEquals(counters['foo'], 1)

    def test_on_message_callback_closed_connection(self):
        counters = {"foo": 0}

        def foo(response):
            counters["foo"] += 1

        self.client.register_callback(foo)

        self.client.on_message(None)

        self.assertEquals(counters['foo'], 0)


if __name__ == '__main__':
    unittest.main()
