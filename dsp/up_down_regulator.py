'''
Created on Apr 4, 2016

@author: William
'''

import time

class UpDownRegulator(object):
    def __init__(self, KPup,KIup,KPdown,KIdown,maximum,minimum):
        self.KPup = KPup
        self.KIup = KIup
        self.KPdown = KPdown
        self.KIdown = KIdown
        self.maximum = maximum
        self.minimum = minimum

        self.time_last = 0.

    def calculate(self,xFbk,xRef):
        now = time.time()
        time_delta = now - self.time_last

        error = xRef - xFbk
        if error > 0.:
            self.KP = self.KPup
            self.KI = self.KIup
        else:
            self.KP = self.KPdown
            self.KI = self.KIdown
    
        self.QP  = error * self.KP
        self.QI += error * self.KI * time_delta
        self.Q = self.QP + self.QI

        #limit with anti-windup applied to integrator
        if self.Q > self.maximum:
            self.Q = self.maximum
            self.QI = self.maximum - self.QP
        elif self.Q < self.minimum:
            self.Q = self.minimum
            self.QI = self.minimum - self.QP

        self.time_last = now
        return self.Q
