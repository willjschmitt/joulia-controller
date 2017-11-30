"""Tests for the arduino module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from measurement.analog_reader import ArduinoAnalogReader
from measurement.analog_reader import MCP3004AnalogReader
from testing.stub_mcp3008 import StubMCP3008
from testing.stub_mcp3008 import StubSpiDev


class StubSmbus(object):
    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.written_bytes = []
        self.channel_to_return = None

        self.bytes_to_return = []

    def write_byte(self, address, byte):
        self.channel_to_return = byte
        self.written_bytes.append((address, byte))

    def read_byte_data(self, unused_address, byte_number):
        assert self.channel_to_return is not None,\
            "You must write_byte before reading"
        return self.bytes_to_return[self.channel_to_return][byte_number]

    def write_read_byte_data(self, address, channel, byte_number, value):
        del address
        while len(self.bytes_to_return) < (channel + 1):
            self.bytes_to_return.append([])
        while len(self.bytes_to_return[channel]) < (byte_number + 1):
            self.bytes_to_return[channel].append(0x00)
        self.bytes_to_return[channel][byte_number] = value


class TestArduinoAnalogReader(unittest.TestCase):
    """Tests for the ArduinoAnalogReader class."""

    def setUp(self):
        self.i2c_bus = StubSmbus(1)
        self.reader = ArduinoAnalogReader(self.i2c_bus, 0x0A, 5.0)

    def test_read(self):
        self.i2c_bus.bytes_to_return = [[], [0x01, 0x02]]
        result = self.reader.read(1)
        self.assertEqual(result, 258)

    def test_read_voltage(self):
        self.i2c_bus.bytes_to_return = [[], [0x01, 0x02]]
        result = self.reader.read_voltage(1)
        self.assertAlmostEqual(result, 1.260, 3)  # 258/1024 * 5.0

    def test_read_voltage_failed(self):
        self.i2c_bus.bytes_to_return = [[], [-1, -1]]
        with self.assertRaises(RuntimeError):
            self.reader.read_voltage(1)

    def test_write_read(self):
        channel = 1
        want = 10
        self.reader.write_read(channel, want)
        got = self.reader.read(channel)
        self.assertEqual(got, want)


class TestMCP3004AnalogReader(unittest.TestCase):
    """Tests for the MCP3004AnalogReader class."""

    def setUp(self):
        self.mcp = StubMCP3008(StubSpiDev())
        self.reader = MCP3004AnalogReader(self.mcp, 5.0)

    def test_read(self):
        self.mcp.set_counts(1, 258)
        result = self.reader.read(1)
        self.assertEqual(result, 258)

    def test_read_voltage(self):
        self.mcp.set_counts(1, 258)
        result = self.reader.read_voltage(1)
        self.assertAlmostEqual(result, 1.260, 3)  # 258/1024 * 5.0

    def test_write_read(self):
        channel = 1
        want = 10
        self.reader.write_read(channel, want)
        got = self.reader.read(channel)
        self.assertEqual(got, want)
