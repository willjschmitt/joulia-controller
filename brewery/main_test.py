"""Tests for the main module."""

import unittest

from brewery.brewhouse import Brewhouse
from main import main
from main import System
from testing.stub_async_http_client import StubAsyncHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestMain(unittest.TestCase):
    """Tests for the main function."""
    pass


class TestCreateBrewhouse(unittest.TestCase):
    """Tests for the create_brewhouse function."""

    def setUp(self):
        self.http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient(
            "fake address", self.http_client)
        self.start_stop_client = StubAsyncHTTPClient()
        self.system = System(self.http_client, self.ws_client,
                             self.start_stop_client)

    def test_create_brewhouse_succeeds(self):
        self.system.create_brewhouse(0)
        self.assertIsInstance(self.system.brewhouse, Brewhouse)

    def test_end_brewing(self):
        self.system.create_brewhouse(0)
        self.system.end_brewing()

    def test_watch_for_start(self):
        self.start_stop_client.messages = {"recipe_instance": 11}
        self.system.watch_for_start()
        self.assertEquals(self.system.brewhouse.recipe_instance, 11)

    def test_watch_for_end(self):
        self.system.create_brewhouse(0)
        self.system.watch_for_end()
