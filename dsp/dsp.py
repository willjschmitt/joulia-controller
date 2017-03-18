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

    Transfer function: H(s) = KP + KI/s.

    Output is limited by forcing the integral portion to offset the proportional
    portion in order to keep the output within the limits. This achieves anti-
    windup.

    Attributes:
        gain_proportional: Proportional gain KP.
        gain_integral: Integral gain KI.
        max_output: Upper limit on the output. Set to None disables limit.
        min_output: Lower limit on the output. Set to None disables limit.
        enabled: Boolean indicating if state should be reset to 0.0 and no
            output should be produced.
    """
    def __init__(self, clock, gain_proportional, gain_integral,
                 max_output=None, min_output=None):
        super(Regulator, self).__init__(clock)

        if max_output is not None and min_output is not None:
            assert min_output < max_output

        self.gain_proportional = gain_proportional
        self.gain_integral = gain_integral
        self.max_output = max_output
        self.min_output = min_output

        self.q_proportional = 0.0
        self.q_integral = 0.0
        self.q = 0.0

        self.time_last = 0.

        self.enabled = False

    def calculate(self, feedback, reference):
        """Solves the regulator block given a measured actual `feedback` and a
        desired `reference` value.

        Args:
            feedback: The present measured value of the signal attempted to be
                controlled.
            reference: The desired value for the controlled signal.
        """
        now = self._time()

        if self.enabled:
            delta = reference - feedback
            delta_time = now - self.time_last
            self.q_proportional = delta * self.gain_proportional
            self.q_integral += delta * self.gain_integral * delta_time
            self.q = self.q_proportional + self.q_integral

            self._limit()
        else:
            self.q = self.q_proportional = self.q_integral = 0.

        self.time_last = now
        return self.q

    def _limit(self):
        """Applies limit to output with anti-windup applied to integrator."""
        if self.max_output is not None and self.q > self.max_output:
            self.q = self.max_output
            self.q_integral = self.max_output - self.q_proportional

        if self.min_output is not None and self.q < self.min_output:
            self.q = self.min_output
            self.q_integral = self.min_output - self.q_proportional

    def enable(self):
        """Enables the regulator."""
        self.enabled = True

    def disable(self):
        """Disables the regulator."""
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