"""Tests for op_amp module."""

import unittest

from op_amp import DifferentialAmplifier
from op_amp import OpAmp
from op_amp import VoltageFollower


class TestOpAmp(unittest.TestCase):
    """Tests the OpAmp class."""

    def setUp(self):
        self.op_amp = OpAmp(2.0)

    def test_v_in(self):
        self.assertAlmostEquals(self.op_amp.v_in(2.0), 1.0, 9)

    def test_v_out(self):
        op_amp = OpAmp(2.0)
        self.assertAlmostEquals(self.op_amp.v_out(2.0), 4.0, 9)


class TestVoltageFollower(unittest.TestCase):
    """Tests the OpAmp class."""

    def setUp(self):
        self.op_amp = VoltageFollower()

    def test_v_in(self):
        self.assertAlmostEquals(self.op_amp.v_in(1.0), 1.0, 9)

    def test_v_out(self):
        self.assertAlmostEquals(self.op_amp.v_out(1.0), 1.0, 9)


class TestDifferentialAmplifier(unittest.TestCase):
    """Tests the DifferentialAmplifier class."""

    def setUp(self):
        self.op_amp = DifferentialAmplifier(1.0, 2.0)

    def test_v_in(self):
        self.assertAlmostEquals(self.op_amp.v_in(1.0), -0.5, 9)

    def test_v_out(self):
        self.assertAlmostEquals(self.op_amp.v_out(1.0), -2.0, 9)
