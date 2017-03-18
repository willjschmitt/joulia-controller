"""Tests for the gpio module."""

import unittest

from measurement.gpio import OutputPin
from testing.stub_gpio import StubGPIO


class TestOutputPin(unittest.TestCase):
    """Tests the OutputPin class."""

    def setUp(self):
        pin = 0
        self.gpio = StubGPIO()
        self.pin = OutputPin(self.gpio, pin)

    def test_get_set(self):
        self.pin.value = self.gpio.HIGH
        self.assertEquals(self.pin.value, self.gpio.HIGH)

    def test_set_on(self):
        self.pin.set_on()
        self.assertEquals(self.pin.value, self.gpio.HIGH)

    def test_set_off(self):
        self.pin.set_off()
        self.assertEquals(self.pin.value, self.gpio.LOW)