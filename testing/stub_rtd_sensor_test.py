"""Tests for the stub_rtd_sensor module."""

import unittest

from testing.stub_rtd_sensor import StubRtdSensor


class TestStubRtdSensor(unittest.TestCase):
    """Tests for the StubRtdSensor class."""

    def test_measure(self):
        sensor = StubRtdSensor(70.0)
        self.assertEquals(sensor.measure_calls, 0)
        self.assertAlmostEquals(sensor.temperature, 70.0, 9)
        sensor.measure()
        self.assertAlmostEquals(sensor.temperature, 70.0, 9)
        self.assertEquals(sensor.measure_calls, 1)
