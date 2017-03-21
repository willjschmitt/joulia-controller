"""Test for the stub_joulia_webserver_client module."""

import unittest

from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestStubJouliaHTTPClient(unittest.TestCase):
    """Tests for the StubJouliaHTTPClient class."""

    def setUp(self):
        self.client = StubJouliaHTTPClient("fake address")

    def test_identify(self):
        self.client.identifier = 11
        sensor_name = "foo"
        recipe_instance = 1
        got = self.client.identify(sensor_name, recipe_instance)
        self.assertEquals(got, 11)
        self.assertEquals(self.client.identifier, 12)

    def test_update_sensor_name(self):
        recipe_instance = 1
        value = 2.0
        sensor = 3
        self.client.update_sensor_value(recipe_instance, value, sensor)
        want = {"recipe_instance": 1, "value": 2.0, "sensor": 3}
        self.assertIn(want, self.client.update_sensor_value_posts)


class TestStubJouliaWebsocketClient(unittest.TestCase):
    """Tests for the StubJouliaWebsocketClient class."""

    def test_create_succeeds(self):
        http_client = StubJouliaHTTPClient("fake address")
        StubJouliaWebsocketClient("fake address", http_client)
