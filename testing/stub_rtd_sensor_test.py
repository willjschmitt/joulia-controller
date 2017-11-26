"""Tests for the stub_rtd_sensor module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from testing.stub_rtd_sensor import StubRtdSensor


class TestStubRtdSensor(unittest.TestCase):
    """Tests for the StubRtdSensor class."""

    def test_measure(self):
        sensor = StubRtdSensor(70.0)
        self.assertEqual(sensor.measure_calls, 0)
        self.assertAlmostEqual(sensor.temperature, 70.0, 9)
        sensor.measure()
        self.assertAlmostEqual(sensor.temperature, 70.0, 9)
        self.assertEqual(sensor.measure_calls, 1)
