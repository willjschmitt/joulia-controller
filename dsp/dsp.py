"""Digital Signal Processing blocks for processing time-domain inputs with
frequency-domain devices.
"""

import time


class DSPBase(object):
    """Abstract class for digital signal processing.

    Attributes:
        clock: The timer object, which `.time()` can be called on to retrieve
            the current time.
        time_last: The last time the DSP block was calculated.
    """
    def __init__(self, clock):
        self.clock = clock
        self.time_last = self._time()

    def _time(self):
        return self.clock.time()


class FirstOrderLag(DSPBase):
    """A first-order low pass filter.

    Transfer function: H(s) = 1/(1+st)
    """
    def __init__(self, clock, tau, init=None):
        super(FirstOrderLag, self).__init__(clock)
        if init is not None:
            self.filtered_last = init
            self.filtered = init
        else:
            self.filtered_last = 0.0
            self.filtered = 0.0

        self.tau = tau

    def filter(self, unfiltered):
        """Performs the filtering of ``unfiltered``."""
        now = self._time()
        delta_time = now - self.time_last
        self.time_last = now
        self.filtered += (unfiltered - self.filtered) * (delta_time / self.tau)


class Integrator(DSPBase):
    """Integrates an incoming signal.

    Transfer function: H(s) = 1/s.

    Attributes:
        integrated: The output (integrated input) of the block.
    """
    def __init__(self, clock, init=None):
        super(Integrator, self).__init__(clock)
        if init is not None:
            self.integrated = init
        else:
            self.integrated = 0.0

    def integrate(self, signal):
        """Integrates the incoming ``signal``."""
        now = self._time()
        time_delta = now - self.time_last
        self.time_last = now

        self.integrated += signal * time_delta


class Regulator(DSPBase):
    """A proportional-integral (PI) Regulator.

    Transfer function: H(s) = KP + KI/s
    """
    def __init__(self, clock, KP=1.,KI=1.,maxQ=0.,minQ=0.):
        super(Regulator, self).__init__(clock)
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


class UpDownRegulator(DSPBase):
    def __init__(self, clock, KPup,KIup,KPdown,KIdown,maximum,minimum):
        super(UpDownRegulator, self).__init__(clock)
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