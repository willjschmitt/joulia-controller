"""Tests for the pump module."""

import unittest

from brewery.pump import SimplePump
from measurement.gpio import OutputPin
from testing.stub_gpio import StubGPIO


class TestSimplePump(unittest.TestCase):
    """Tests for the SimplePump class."""

    def setUp(self):
        self.gpio = StubGPIO()
        self.pin = OutputPin(self.gpio, 1)
        self.pump = SimplePump(self.pin)

    def test_turn_off(self):
        self.pump.turn_off()
        self.assertFalse(self.pump.enabled)
        self.assertEquals(self.pin.value, self.gpio.LOW)

    def test_turn_on(self):
        self.pump.turn_on()
        self.assertTrue(self.pump.enabled)
        self.assertEquals(self.pin.value, self.gpio.HIGH)
