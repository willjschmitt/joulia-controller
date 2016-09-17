'''
Created on Apr 3, 2016

@author: William
'''

import time

class Integrator(object):
    """Integrates an incoming signal

    Transfer function: H(s) = 1/s
    """
    def __init__(self, **kwargs):
        if 'init' in kwargs:
            self.integrated = kwargs['init']
        else:
            self.integrated = 0.

        self.time_last = time.time()

    def integrate(self,signal):
        """Integrates the incoming ``signal``"""
        now = time.time()
        time_delta = now - self.time_last
        self.time_last = now

        self.integrated += signal * time_delta
