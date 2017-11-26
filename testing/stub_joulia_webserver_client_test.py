"""Test for the stub_joulia_webserver_client module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest
from unittest.mock import Mock

from joulia_webserver import client
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
        sensor_id = self.client.identify(sensor_name, recipe_instance,
                                         client.OVERRIDE_VARIABLE_TYPE)
        self.assertEqual(sensor_id, 11)
        self.assertEqual(self.client.identifier, 12)

    def test_update_sensor_name(self):
        recipe_instance = 1
        value = 2.0
        sensor = 3
        self.client.update_sensor_value(recipe_instance, value, sensor)
        want = {"recipe_instance": 1, "value": 2.0, "sensor": 3}
        self.assertIn(want, self.client.update_sensor_value_posts)

    def test_get_mash_points(self):
        recipe_instance_pk = 3
        mash_points = [(15.0, 170.0)]
        self.client.mash_points = mash_points
        got = self.client.get_mash_points(recipe_instance_pk)
        self.assertEqual(got, mash_points)

    def test_get_recipe_instance_assert_fails(self):
        recipe_instance_pk = 10
        with self.assertRaises(AssertionError):
            self.client.get_recipe_instance(recipe_instance_pk)

    def test_get_recipe_instance(self):
        recipe_instance_pk = 10
        recipe_instance = Mock()
        self.client.recipe_instance = recipe_instance
        got = self.client.get_recipe_instance(recipe_instance_pk)
        self.assertIs(got, recipe_instance)

    def test_get_recipe_assert_fails(self):
        recipe_pk = 3
        with self.assertRaises(AssertionError):
            self.client.get_recipe(recipe_pk)

    def test_get_recipe(self):
        recipe_pk = 3
        recipe = Mock()
        self.client.recipe = recipe
        got = self.client.get_recipe(recipe_pk)
        self.assertIs(got, recipe)

    def test_get_brewhouse(self):
        brewhouse_pk = 2
        brewhouse = Mock()
        self.client.brewhouse = brewhouse
        got = self.client.get_brewhouse(brewhouse_pk)
        self.assertIs(got, brewhouse)


class TestStubJouliaWebsocketClient(unittest.TestCase):
    """Tests for the StubJouliaWebsocketClient class."""

    def test_create_succeeds(self):  # pylint: disable=no-self-use
        http_client = StubJouliaHTTPClient("fake address")
        StubJouliaWebsocketClient("fake address", http_client)
