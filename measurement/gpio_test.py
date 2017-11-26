"""Tests for the gpio module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

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
        self.assertEqual(self.pin.value, self.gpio.HIGH)

    def test_set_on(self):
        self.pin.set_on()
        self.assertEqual(self.pin.value, self.gpio.HIGH)

    def test_set_off(self):
        self.pin.set_off()
        self.assertEqual(self.pin.value, self.gpio.LOW)
