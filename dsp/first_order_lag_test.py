"""Tests for first_order_lag module."""

import unittest

from dsp.first_order_lag import FirstOrderLag


class StubFirstOrderLag(FirstOrderLag):
    def __init__(self, tau, init=None):
        self._time_counter = -1.0
        super(StubFirstOrderLag, self).__init__(tau, init=init)

    def _time(self):
        self._time_counter += 1.0
        return float(self._time_counter)


class TestFirstOrderLag(unittest.TestCase):
    """Tests for the FirstOrderLag class."""

    def test_construct_without_init(self):
        fil = FirstOrderLag(1.0)
        self.assertAlmostEquals(fil.filtered, 0.0, 9)
        self.assertAlmostEquals(fil.filtered_last, 0.0, 9)

    def test_construct_with_init(self):
        fil = FirstOrderLag(1.0, init=11.0)
        self.assertAlmostEquals(fil.filtered, 11.0, 9)
        self.assertAlmostEquals(fil.filtered_last, 11.0, 9)

    def test_filter(self):
        fil = StubFirstOrderLag(300.0)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 6.3, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 8.7, 1)

        for _ in range(300):
            fil.filter(10.0)
        self.assertAlmostEquals(fil.filtered, 9.5, 1)
