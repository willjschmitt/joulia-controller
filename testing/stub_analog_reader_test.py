"""Tests for testing.stub_arduino module."""

import unittest

from testing.stub_analog_reader import StubAnalogReader


class TestStubAnalogReader(unittest.TestCase):
    """Tests for the StubAnalogReader class."""

    def test_read(self):
        reader = StubAnalogReader()
        reader.voltage = 123.45
        channel = 0
        self.assertEquals(reader.read_voltage(channel), 123.45)
