"""Tests for the circuits module."""

import unittest

from measurement.circuits import VariableResistanceVoltageDivider
from measurement.circuits import VoltageDivider


class TestVoltageDivider(unittest.TestCase):
    """Tests the VoltageDivider class."""

    def setUp(self):
        resistance_top = 90.0
        resistance_bottom = 10.0
        self.voltage_divider = VoltageDivider(resistance_top, resistance_bottom)

    def test_transfer_function(self):
        self.assertAlmostEquals(self.voltage_divider.transfer_function, 0.1, 9)

    def test_v_in(self):
        self.assertAlmostEquals(self.voltage_divider.v_in(10.0), 100.0, 9)

    def test_v_out(self):
        self.assertAlmostEquals(self.voltage_divider.v_out(10.0), 1.0, 9)


class TestVariableResistanceVoltageDivider(unittest.TestCase):
    """Tests the VariableResistanceVoltageDivider class."""

    def setUp(self):
        resistance_top = 90.0
        voltage_in = 1.0
        self.voltage_divider = VariableResistanceVoltageDivider(
            resistance_top, voltage_in)

    def test_v_out(self):
        self.assertAlmostEquals(self.voltage_divider.v_out(10.0), 0.1, 9)

    def test_resistance_bottom(self):
        self.assertAlmostEquals(
            self.voltage_divider.resistance_bottom(0.1), 10.0, 9)
