"""Tests for the brewhouse module."""

import unittest

from brewery.brewhouse import Brewhouse
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestBrewhouse(unittest.TestCase):
    """Tests for the Brewhouse class."""

    def setUp(self):
        self.gpio = StubGPIO()
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)

    def test_create_succeeds(self):
        recipe_instance = 0
        Brewhouse(self.ws_client, self.gpio, recipe_instance)
