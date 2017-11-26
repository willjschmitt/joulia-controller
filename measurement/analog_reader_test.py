"""Tests for the arduino module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from measurement.analog_reader import ArduinoAnalogReader


class StubSmbus(object):
    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.written_bytes = []

        self.bytes_to_return = []

    def write_byte(self, address, byte):
        self.written_bytes.append((address, byte))

    def read_byte_data(self, unused_address, byte_number):
        return self.bytes_to_return[byte_number]


class TestArduinoAnalogReader(unittest.TestCase):
    """Tests for the ArduinoAnalogReader class."""

    def setUp(self):
        self.smbus = StubSmbus(1)
        self.reader = ArduinoAnalogReader(self.smbus, 0x0A, 5.0)

    def test_read(self):
        self.smbus.bytes_to_return = [0x01, 0x02]
        result = self.reader.read(1)
        self.assertEqual(result, 258)

    def test_read_voltage(self):
        self.smbus.bytes_to_return = [0x01, 0x02]
        result = self.reader.read_voltage(1)
        self.assertAlmostEqual(result, 1.260, 3)  # 258/1024 * 5.0

    def test_read_voltage_failed(self):
        self.smbus.bytes_to_return = [-1, -1]
        with self.assertRaises(RuntimeError):
            self.reader.read_voltage(1)
