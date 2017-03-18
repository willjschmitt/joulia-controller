"""Tests for dsp module."""

import unittest

from dsp.dsp import DSPBase
from dsp.dsp import FirstOrderLag


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
        self.assertIsNotNone(self.dsp._time())


class TestFirstOrderLag(unittest.TestCase):
    """Tests for the FirstOrderLag class."""

    def test_construct_without_init(self):
        fil = FirstOrderLag(StubClock(), 1.0)
        self.assertAlmostEquals(fil.filtered, 0.0, 9)
        self.assertAlmostEquals(fil.filtered_last, 0.0, 9)

    def test_construct_with_init(self):
        fil = FirstOrderLag(StubClock(), 1.0, init=11.0)
        self.assertAlmostEquals(fil.filtered, 11.0, 9)
        self.assertAlmostEquals(fil.filtered_last, 11.0, 9)

    def test_filter(self):
        fil = FirstOrderLag(StubClock(), 300.0)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 6.3, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 8.7, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 9.5, 1)