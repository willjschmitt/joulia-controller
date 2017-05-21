"""Tests for the rtd_sensor module."""

import unittest

from measurement.rtd_sensor import RtdSensor
from measurement.rtd_sensor import celsius_to_fahrenheit
from testing.stub_analog_reader import StubAnalogReader


class TestRtdSensor(unittest.TestCase):
    """Tests for RtdSensor class."""

    def setUp(self):
        analog_pin = 0
        alpha = 0.00385
        zero_resistance = 100.0
        analog_reference_voltage = 3.3
        tau = 10.0
        self.vcc = 3.3

        # RTD
        # 0.300V at Freezing
        # 0.401V at Boiling
        resistance_rtd_top = 1000.0

        # Amplifies differential by 18.0x
        amplifier_resistance_a = 15000.0
        amplifier_resistance_b = 270000.0

        # Offset will be 0.3V
        offset_resistance_bottom = 10000.0
        offset_resistance_top = 100000.0

        # Sensor overall will be:
        # 0.000V at Freezing
        # 1.826V at Boiling

        self.analog_reader = StubAnalogReader()
        self.rtd = RtdSensor(
            self.analog_reader, analog_pin, alpha, zero_resistance,
            analog_reference_voltage, tau, self.vcc, resistance_rtd_top,
            amplifier_resistance_a, amplifier_resistance_b,
            offset_resistance_bottom, offset_resistance_top)

    def test_temperature_not_set(self):
        self.assertAlmostEquals(self.rtd.temperature_unfiltered, 0.0, 9)

    def test_resistance_to_temperature_freezing(self):
        measured = self.rtd._resistance_to_temperature(100.0)
        self.assertAlmostEquals(measured, 32.0, 9)

    def test_resistance_to_temperature_boiling(self):
        measured = self.rtd._resistance_to_temperature(138.5)
        self.assertAlmostEquals(measured, 212.0, 9)

    def test_measure_freezing(self):
        self.analog_reader.voltage = 0.0
        self.rtd.measure()
        self.assertAlmostEquals(self.rtd.temperature_unfiltered, 32.0, 9)

    def test_measure_boiling(self):
        self.analog_reader.voltage = 1.827
        self.rtd.measure()
        self.assertAlmostEquals(self.rtd.temperature_unfiltered, 212.0, 0)

    def test_temperature_property(self):
        self.assertAlmostEquals(self.rtd.temperature, 0.0, 9)


class TestCelsiusToFahrenheit(unittest.TestCase):
    """Tests the celsius_to_fahrenheit function."""

    def test_freezing(self):
        self.assertAlmostEquals(celsius_to_fahrenheit(0.0), 32.0, 9)

    def test_boiling(self):
        self.assertAlmostEquals(celsius_to_fahrenheit(100.0), 212.0, 9)
