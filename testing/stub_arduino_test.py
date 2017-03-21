"""Tests for testing.stub_arduino module."""

import unittest

from testing.stub_arduino import StubAnalogReader


class TestStubAnalogReader(unittest.TestCase):
    """Tests for the StubAnalogReader class."""

    def test_read(self):
        i2c_bus = None
        address = None
        reader = StubAnalogReader(i2c_bus, address)
        reader.counts = 100
        channel = 0
        self.assertEquals(reader.read(channel), 100)