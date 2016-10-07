'''
Created on Apr 3, 2016

@author: William
'''

import time

class Regulator(object):
    """A proportional-integral (PI) Regulator.

    Transfer function: H(s) = KP + KI/s
    """
    def __init__(self,KP=1.,KI=1.,maxQ=0.,minQ=0.):
        self.KP = KP
        self.KI = KI
        self.maxQ = maxQ
        self.minQ = minQ

        self.QI = 0.

        self.time_last = 0.

        self.enabled = False

    def calculate(self,xFbk,xRef):
        now = time.time()

        if self.enabled:
            self.QP  = (xRef-xFbk) * self.KP
            self.QI += (xRef-xFbk) * self.KI * (now-self.time_last)
            self.Q = self.QP + self.QI

            #limit with anti-windup applied to integrator
            if self.Q > self.maxQ:
                self.Q = self.maxQ
                self.QI = self.maxQ - self.QP
            elif self.Q < self.minQ:
                self.Q = self.minQ
                self.QI = self.minQ - self.QP
        else:
            self.Q = self.QP = self.QI = 0.

        self.time_last = now
        return self.Q

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
