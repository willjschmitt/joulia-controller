'''
Created on Apr 3, 2016

@author: William
'''

import time

class FirstOrderLag(object):
    """A first-order low pass filter

    Transfer function: H(s) = 1/(1+st)
    """
    def __init__(self, tau, **kwargs):
        if 'init' in kwargs:
            self.filtered_last = kwargs['init']
            self.filtered = kwargs['init']
        else:
            self.filtered_last = 0.
            self.filtered = 0.

        self.time_last = time.time()
        self.tau = tau

    def filter(self,unfiltered):
        """Performs the filtering of ``unfiltered``"""
        now = time.time()
        delta_time = now - self.time_last
        self.time_last = now

        self.filtered += (unfiltered - self.filtered) * (delta_time / self.tau)
