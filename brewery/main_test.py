"""Tests for the main module."""

import unittest

from brewery.brewhouse import Brewhouse
from main import main
from main import create_brewhouse
from main import create_analog_reader
from main import watch_for_start
from main import watch_for_end
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient

class TestMain(unittest.TestCase):
    """Tests for the main function."""
    pass


class TestCreateBrewhouse(unittest.TestCase):
    """Tests for the create_brewhouse function."""

    def test_succeeds(self):
        http_client = StubJouliaHTTPClient("fake address")
        ws_client = StubJouliaWebsocketClient("fake address", http_client)
        brewhouse = create_brewhouse(ws_client, "localhost:8888", 0)
        self.assertIsInstance(brewhouse, Brewhouse)
