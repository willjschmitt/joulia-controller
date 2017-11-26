"""Helpers for working with operational amplifiers and typical linear circuits.
"""


class OpAmp(object):
    """Represents an operational amplifier.

    Attributes:
        transfer_function: Simple scalar ratio relating output to input on the
            amplifier.
    """

    def __init__(self, transfer_function):
        self.transfer_function = transfer_function

    def v_in(self, v_out):
        """Returns the calculated input based on the observed output."""
        return v_out / self.transfer_function

    def v_out(self, v_in):
        """Returns the expected output based on an input."""
        return v_in * self.transfer_function


class VoltageFollower(OpAmp):
    """A voltage follower op-amp circuit."""

    def __init__(self):
        super(VoltageFollower, self).__init__(1.0)


class DifferentialAmplifier(OpAmp):
    """A differential op-amp circuit.

    Attributes:
        resistance_1: Input resistors into the op-amp for the two signals to
            difference. Units: Ohms.
        resistance_2: Feedback resistors around the op-amp. Units: Ohms.
    """

    def __init__(self, resistance_1, resistance_2):
        transfer_function = -resistance_2 / resistance_1
        super(DifferentialAmplifier, self).__init__(transfer_function)
