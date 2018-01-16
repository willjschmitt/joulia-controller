"""Tests for joulia_webserver.client module."""

import json
import unittest

from joulia_webserver import client
from joulia_webserver.client import JouliaHTTPClient
from joulia_webserver.client import JouliaWebserverClientBase
from joulia_webserver.client import JouliaWebsocketClient
from joulia_webserver.models import MashStep
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_requests import StubRequests
from testing.stub_websocket import stub_websocket_connect


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
            self.client.identify(sensor_name, recipe_instance,
                                 client.VALUE_VARIABLE_TYPE)

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


class TestJouliaHttpClient(unittest.TestCase):
    """Tests JouliaHttpClient."""

    def setUp(self):
        self.address = "http://fakehost"
        self.client = JouliaHTTPClientTest(self.address, auth_token=None)

    def test_post(self):
        self.client._requests_service.response_string = '{"foo":"bar"}'
        response = self.client._post("fakeurl", data={'baz': 1})
        self.assertEqual(response.json(), {"foo": "bar"})

    def test_get(self):
        self.client._requests_service.response_string = '{"foo":"bar"}'
        response = self.client._get("fakeurl")
        self.assertEqual(response.json(), {"foo": "bar"})

    def test_get_brewhouse_id_url(self):
        got = self.client._get_brewhouse_id_url
        want = "http://fakehost/brewery/api/brewhouse_from_token/"
        self.assertEqual(got, want)

    def test_get_brewhouse_id(self):
        self.client._requests_service.response_string = '{"brewhouse":11}'
        got = self.client.get_brewhouse_id()
        want = 11
        self.assertEqual(got, want)

    def test_identify_url(self):
        got = self.client._identify_url
        want = "http://fakehost/live/timeseries/identify/"
        self.assertEqual(got, want)

    def test_identify(self):
        self.client._requests_service.response_string = (
            '{"sensor":11}')
        sensor_name = "fake_sensor"
        recipe_instance = 1
        sensor_id = self.client.identify(
            sensor_name, recipe_instance, client.OVERRIDE_VARIABLE_TYPE)
        self.assertEqual(sensor_id, 11)

    def test_update_sensor_value_url(self):
        got = self.client._update_sensor_value_url
        want = "http://fakehost/live/timeseries/new/"
        self.assertEqual(got, want)

    def test_update_sensor_value(self):
        self.client._requests_service.response_string = '{"sensor":11}'
        recipe_instance = 1
        value = 2.0
        sensor_id = 3
        self.client.update_sensor_value(recipe_instance, value, sensor_id)

    def test_get_mash_points(self):
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/mash_point/?recipe=10"] = (
                '[{"time":60.0,"temperature":152.0},'
                '{"time":15.0,"temperature":160.0}]')
        got = self.client.get_mash_points(10)
        want = [MashStep(60.0, 152.0), MashStep(15.0, 160.0)]
        self.assertEquals(got, want)

    def test_get_recipe_instance(self):
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/recipeInstance/3/"] = (
                '{"id":3,"recipe":10}')
        got = self.client.get_recipe_instance(3)
        self.assertEquals(got.pk, 3)
        self.assertEquals(got.recipe_pk, 10)

    def test_get_recipe(self):
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/mash_point/?recipe=10"] = (
            '['
                '{"time":60.0,"temperature":152.0},'
                '{"time":15.0,"temperature":160.0}'
            ']')
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/recipe/10/"] = (
            '{'
                '"id":10,'
                '"strike_temperature":170.0,'
                '"mashout_temperature":170.0,'
                '"mashout_time":15,'
                '"boil_time":60,'
                '"cool_temperature":70.0'
            '}')
        recipe = self.client.get_recipe(10)
        self.assertEquals(recipe.pk, 10)
        self.assertEquals(recipe.strike_temperature, 170.0)
        self.assertEquals(recipe.mashout_temperature, 170.0)
        self.assertEquals(recipe.mashout_time, 15)
        self.assertEquals(recipe.boil_time, 60)
        self.assertEquals(recipe.cool_temperature, 70.0)

    def test_get_latest_joulia_controller_release(self):
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/joulia_controller_release/"] = (
            '['
                '{"commit_hash":3}'
            ']')
        got = self.client.get_latest_joulia_controller_release()
        self.assertEquals(got["commit_hash"], 3)

    def test_get_latest_joulia_controller_release_no_releases(self):
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/joulia_controller_release/"] = '[]'
        got = self.client.get_latest_joulia_controller_release()
        self.assertEquals(got["commit_hash"], None)

    def test_get_brewhouse(self):
        with open('testing/brewhouse.json') as brewhouse_file:
            brewhouse_data = brewhouse_file.read()
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/brewhouse/9/"] = brewhouse_data
        got = self.client.get_brewhouse(9)
        self.assertEquals(got, json.loads(brewhouse_data))

    def test_update_brewhouse(self):
        with open('testing/brewhouse.json') as brewhouse_file:
            brewhouse_data = brewhouse_file.read()
            parsed_brewhouse_data = json.loads(brewhouse_data)
        self.client._requests_service.response_map[
            "http://fakehost/brewery/api/brewhouse/9/"] = brewhouse_data
        got = self.client.update_brewhouse(parsed_brewhouse_data)
        self.assertEquals(got, parsed_brewhouse_data)


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
        sensor_id = self.client.identify(
            sensor_name, recipe_instance, client.OVERRIDE_VARIABLE_TYPE)
        self.assertEqual(sensor_id, 11)

    def check_subscription(self, message_index, recipe_instance, sensor):
        """Checks that a subscription request was sent to websocket.

        Args:
            message_index: Which message should be checked.
            recipe_instance: The recipe instance that should have been
                subscribed.
            sensor: the sensor in the recipe_instance to subscribe to.
        """
        got = self.client.websocket.written_messages[message_index]
        parsed = json.loads(got)
        self.assertEquals(parsed['recipe_instance'], recipe_instance)
        self.assertEquals(parsed['sensor'], sensor)
        self.assertEquals(parsed['subscribe'], True)

    def test_subscribe(self):
        recipe_instance = 1
        sensor = 3
        self.client.subscribe(recipe_instance, sensor)

        self.check_subscription(0, recipe_instance, sensor)

        subscription = JouliaWebsocketClient.Subscription(
            recipe_instance=recipe_instance, sensor=sensor)
        self.assertEquals(self.client._subscriptions, {subscription})

    def test_register_callback(self):
        def foo(_):
            pass  # pragma: no cover

        self.client.register_callback(foo)

        self.assertIn(foo, self.client.callbacks)

    def test_on_message_callback(self):
        counters = {"foo": 0}

        def foo(response):
            counters["foo"] += 1

        self.client.register_callback(foo)

        self.client.on_message("")

        self.assertEquals(counters['foo'], 1)

    def test_on_message_closed_connection(self):
        # Make a subscription first.
        recipe_instance = 1
        sensor = 3
        self.client.subscribe(recipe_instance, sensor)
        subscribe_index = 0
        self.check_subscription(subscribe_index, recipe_instance, sensor)

        # Register a callback.
        counters = {"foo": 0}
        def foo(response):
            counters["foo"] += 1  # pragma: no cover
        self.client.register_callback(foo)

        # Store the current websocket, which will get reset shortly.
        original_socket = self.client.websocket

        # Close the connection.
        self.client.on_message(None)

        # No callbacks should be called on closed connection.
        self.assertEquals(counters['foo'], 0)

        # There should be a new websocket formed. Check that it changed.
        self.assertIsNot(original_socket, self.client.websocket)

        # Subscriptions should be re-performed on close. The client is a new one
        # so the index has reset.
        resubscribe_index = 0
        self.check_subscription(resubscribe_index, recipe_instance, sensor)
