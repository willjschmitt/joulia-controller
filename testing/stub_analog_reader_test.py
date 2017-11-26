"""Tests for testing.stub_arduino module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from testing.stub_analog_reader import StubAnalogReader


class TestStubAnalogReader(unittest.TestCase):
    """Tests for the StubAnalogReader class."""

    def test_read(self):
        reader = StubAnalogReader()
        reader.voltage = 123.45
        channel = 0
        self.assertEqual(reader.read_voltage(channel), 123.45)
