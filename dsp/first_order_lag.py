"""First Order Lag filters."""

import time


class FirstOrderLag(object):
    """A first-order low pass filter.

    Transfer function: H(s) = 1/(1+st)
    """
    def __init__(self, tau, init=None):
        if init is not None:
            self.filtered_last = init
            self.filtered = init
        else:
            self.filtered_last = 0.
            self.filtered = 0.

        self.time_last = self._time()
        self.tau = tau

    def _time(self):
        return time.time()

    def filter(self, unfiltered):
        """Performs the filtering of ``unfiltered``."""
        now = self._time()
        delta_time = now - self.time_last
        self.time_last = now
        self.filtered += (unfiltered - self.filtered) * (delta_time / self.tau)
