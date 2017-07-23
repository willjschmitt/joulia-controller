"""Tests for the pump module."""

import unittest

from brewery.pump import SimplePump
from measurement.gpio import OutputPin
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestSimplePump(unittest.TestCase):
    """Tests for the SimplePump class."""

    def setUp(self):
        self.recipe_instance = 0
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)

        self.gpio = StubGPIO()
        self.pin = OutputPin(self.gpio, 1)
        self.pump = SimplePump(self.ws_client, self.recipe_instance, self.pin)

    def test_turn_off(self):
        self.pump.turn_off()
        self.assertFalse(self.pump.enabled)
        self.assertEquals(self.pin.value, self.gpio.LOW)

    def test_turn_on(self):
        self.pump.turn_on()
        self.assertTrue(self.pump.enabled)
        self.assertEquals(self.pin.value, self.gpio.HIGH)

    def test_turn_on_with_emergency_stop_on(self):
        self.pump.emergency_stop = True
        self.pump.turn_on()
        self.assertFalse(self.pump.enabled)
        self.assertEquals(self.pin.value, self.gpio.LOW)

    def test_from_json(self):
        configuration = {
            "pin": 1,
        }
        SimplePump.from_json(self.ws_client, self.gpio, self.recipe_instance,
                             configuration)
