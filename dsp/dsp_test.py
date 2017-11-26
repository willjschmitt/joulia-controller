"""Tests for dsp module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from dsp.dsp import DSPBase
from dsp.dsp import FirstOrderLag
from dsp.dsp import Integrator
from dsp.dsp import Regulator
from dsp.dsp import UpDownRegulator


class StubClock(object):
    def __init__(self):
        self._time_counter = -1.0

    def time(self):
        self._time_counter += 1.0
        return float(self._time_counter)


class TestDSPBase(unittest.TestCase):
    """Tests for the DSPBase class."""
    def setUp(self):
        self.dsp = DSPBase(StubClock())

    def test_time_succeeds(self):
        self.assertIsNotNone(self.dsp._time())  # pylint: disable=protected-access


class TestFirstOrderLag(unittest.TestCase):
    """Tests for the FirstOrderLag class."""

    def test_construct_without_init(self):
        fil = FirstOrderLag(StubClock(), 1.0)
        self.assertAlmostEqual(fil.filtered, 0.0, 9)
        self.assertAlmostEqual(fil.filtered_last, 0.0, 9)

    def test_construct_with_init(self):
        fil = FirstOrderLag(StubClock(), 1.0, init=11.0)
        self.assertAlmostEqual(fil.filtered, 11.0, 9)
        self.assertAlmostEqual(fil.filtered_last, 11.0, 9)

    def test_filter(self):
        fil = FirstOrderLag(StubClock(), 300.0)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEqual(fil.filtered, 6.3, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEqual(fil.filtered, 8.7, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEqual(fil.filtered, 9.5, 1)


class TestIntegrator(unittest.TestCase):
    """Tests for the Integrator class."""

    def test_construct_without_init(self):
        integrator = Integrator(StubClock())
        self.assertAlmostEqual(integrator.integrated, 0.0, 9)

    def test_construct_with_init(self):
        integrator = Integrator(StubClock(), init=11.0)
        self.assertAlmostEqual(integrator.integrated, 11.0, 9)

    def test_integrate(self):
        integrator = Integrator(StubClock())
        for _ in range(10):
            integrator.integrate(10)
        self.assertAlmostEqual(integrator.integrated, 100.0, 9)


class TestRegulator(unittest.TestCase):
    """Tests for the Regulator class."""

    def setUp(self):
        self.regulator = Regulator(StubClock(), 1.0, 10.0)

    def test_regulate_disabled(self):
        self.regulator.disable()
        feedback = 11.0
        reference = 12.0
        self.regulator.calculate(feedback, reference)

        self.assertAlmostEqual(self.regulator.q_proportional, 0.0, 9)
        self.assertAlmostEqual(self.regulator.q_integral, 0.0, 9)
        self.assertAlmostEqual(self.regulator.output, 0.0, 9)

    def test_regulate_enabled(self):
        self.regulator.enable()
        feedback = 11.0
        reference = 12.0
        self.regulator.calculate(feedback, reference)

        self.assertAlmostEqual(self.regulator.q_proportional, 1.0, 9)
        self.assertAlmostEqual(self.regulator.q_integral, 10.0, 9)
        self.assertAlmostEqual(self.regulator.output, 11.0, 9)

    def test_regulate_max_output(self):
        self.regulator = Regulator(StubClock(), 1.0, 10.0, max_output=0.5)
        self.regulator.enable()
        feedback = 11.0
        reference = 12.0
        self.regulator.calculate(feedback, reference)

        self.assertAlmostEqual(self.regulator.q_proportional, 1.0, 9)
        self.assertAlmostEqual(self.regulator.q_integral, -0.5, 9)
        self.assertAlmostEqual(self.regulator.output, 0.5, 9)

    def test_regulate_min_output(self):
        self.regulator = Regulator(StubClock(), 1.0, 10.0, min_output=-0.5)
        self.regulator.enable()
        feedback = 12.0
        reference = 11.0
        self.regulator.calculate(feedback, reference)

        self.assertAlmostEqual(self.regulator.q_proportional, -1.0, 9)
        self.assertAlmostEqual(self.regulator.q_integral, +0.5, 9)
        self.assertAlmostEqual(self.regulator.output, -0.5, 9)

    def test_bad_limits(self):
        with self.assertRaises(AssertionError):
            Regulator(StubClock(), 1.0, 10.0, min_output=0.5, max_output=-0.5)

    def test_enable(self):
        self.regulator.enabled = False
        self.regulator.enable()
        self.assertTrue(self.regulator.enabled)

    def test_disable(self):
        self.regulator.enabled = False
        self.regulator.disable()
        self.assertFalse(self.regulator.enabled)


class TestUpDownRegulator(unittest.TestCase):
    """Tests the UpDownRegulator class."""

    def test_gains_positive_error(self):
        gain_proportional_up = 12.0
        gain_integral_up = 13.0
        gain_proportional_down = 2.0
        gain_integral_down = 3.0
        regulator = UpDownRegulator(
            StubClock(), gain_proportional_up, gain_integral_up,
            gain_proportional_down, gain_integral_down)

        regulator.calculate(10.0, 11.0)
        self.assertAlmostEqual(
            regulator.gain_proportional, gain_proportional_up, 9)
        self.assertAlmostEqual(
            regulator.gain_integral, gain_integral_up, 9)

    def test_gains_negative_error(self):
        gain_proportional_up = 12.0
        gain_integral_up = 13.0
        gain_proportional_down = 2.0
        gain_integral_down = 3.0
        regulator = UpDownRegulator(
            StubClock(), gain_proportional_up, gain_integral_up,
            gain_proportional_down, gain_integral_down)

        regulator.calculate(11.0, 10.0)
        self.assertAlmostEqual(
            regulator.gain_proportional, gain_proportional_down, 9)
        self.assertAlmostEqual(
            regulator.gain_integral, gain_integral_down, 9)
