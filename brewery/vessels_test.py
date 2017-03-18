"""Tests for the vessesls module."""

import unittest

from brewery.vessels import SimpleVessel
from brewery.vessels import TemperatureMonitoredVessel


class TestSimpleVessel(unittest.TestCase):
    """Tests for the SimpleVessel class."""

    def setUp(self):
        volume = 5.0
        self.vessel = SimpleVessel(volume)

    def test_set_liquid_level(self):
        volume = 10.0
        self.vessel.set_liquid_level(volume)
        self.assertAlmostEquals(self.vessel.volume, volume)


class TestTemperatureMonitoredVessel(unittest.TestCase):
    """Tests for the TemperatureMonitoredVessel class."""

    def setUp(self):
        class StubRtdSensor(object):
            """Fakes a measured temperature with a set temperature."""
            def __init__(self, temperature):
                self.temperature = temperature

                self.measure_calls = 0

            def measure(self):
                self.measure_calls += 1

        volume = 5.0
        self.temperature_sensor = StubRtdSensor(68.0)
        self.vessel = TemperatureMonitoredVessel(
            volume, self.temperature_sensor)

    def test_measure_temperature(self):
        self.assertEquals(self.temperature_sensor.measure_calls, 0)
        self.vessel.measure_temperature()
        self.assertEquals(self.temperature_sensor.measure_calls, 1)

    def test_temperature(self):
        self.temperature_sensor.temperature = 70.0
        self.assertAlmostEquals(self.vessel.temperature, 70.0, 9)
