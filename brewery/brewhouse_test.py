"""Tests for the brewhouse module."""

import unittest

from brewery.brewhouse import Brewhouse
from testing.stub_arduino import StubAnalogReader
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestBrewhouse(unittest.TestCase):
    """Tests for the Brewhouse class."""

    def setUp(self):
        self.gpio = StubGPIO()
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)
        recipe_instance = 0
        i2c_bus = None
        i2c_address = 0x0A
        self.analog_reader = StubAnalogReader(i2c_bus, i2c_address)
        self.brewhouse = Brewhouse(
            self.ws_client, self.gpio, self.analog_reader, recipe_instance)

    def test_create_succeeds(self):
        recipe_instance = 0
        Brewhouse(
            self.ws_client, self.gpio, self.analog_reader, recipe_instance)

    def test_start_brewing_succeeds(self):
        self.brewhouse.start_brewing()

    def test_initialize_recipe_succeeds(self):
        self.brewhouse.initialize_recipe()

    def test_start_timers(self):
        self.brewhouse.start_timers()

    def test_stop_timers(self):
        self.brewhouse.start_timers()
        self.brewhouse.cancel_timers()

    def test_task00(self):
        self.brewhouse.task00()