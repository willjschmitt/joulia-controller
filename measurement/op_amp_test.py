"""Tests for op_amp module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from measurement.op_amp import DifferentialAmplifier
from measurement.op_amp import OpAmp
from measurement.op_amp import VoltageFollower


class TestOpAmp(unittest.TestCase):
    """Tests the OpAmp class."""

    def setUp(self):
        self.op_amp = OpAmp(2.0)

    def test_v_in(self):
        self.assertAlmostEqual(self.op_amp.v_in(2.0), 1.0, 9)

    def test_v_out(self):
        self.assertAlmostEqual(self.op_amp.v_out(2.0), 4.0, 9)


class TestVoltageFollower(unittest.TestCase):
    """Tests the OpAmp class."""

    def setUp(self):
        self.op_amp = VoltageFollower()

    def test_v_in(self):
        self.assertAlmostEqual(self.op_amp.v_in(1.0), 1.0, 9)

    def test_v_out(self):
        self.assertAlmostEqual(self.op_amp.v_out(1.0), 1.0, 9)


class TestDifferentialAmplifier(unittest.TestCase):
    """Tests the DifferentialAmplifier class."""

    def setUp(self):
        self.op_amp = DifferentialAmplifier(1.0, 2.0)

    def test_v_in(self):
        self.assertAlmostEqual(self.op_amp.v_in(1.0), -0.5, 9)

    def test_v_out(self):
        self.assertAlmostEqual(self.op_amp.v_out(1.0), -2.0, 9)
