"""Tests for the arduino module."""

import unittest

from measurement.arduino import AnalogReader


class StubSmbus(object):
    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.written_bytes = []

        self.bytes_to_return = []

    def write_byte(self, address, byte):
        self.written_bytes.append((address, byte))

    def read_byte_data(self, address, byte_number):
        return self.bytes_to_return[byte_number]


class TestAnalogReader(unittest.TestCase):
    """Tests for the analog_read function."""

    def setUp(self):
        self.smbus = StubSmbus(1)
        self.reader = AnalogReader(self.smbus, 0x0A)

    def test_read(self):
        self.smbus.bytes_to_return = [0x01, 0x02]
        result = self.reader.read(1)
        self.assertEquals(result, 258)
