"""General helper classes for calculating the results of simple circuits.
"""


class VoltageDivider(object):
    """A simple voltage divider with an input and ouput resistor to reduce the
    input voltage to a lower value.

    Attributes:
        resistance_top: the input resistor for the divider. Units: Ohms.
        resistance_bottom: the output resistor for the divider. Units: Ohms.
    """

    def __init__(self, resistance_top, resistance_bottom):
        self.resistance_top = resistance_top
        self.resistance_bottom = resistance_bottom

    @property
    def transfer_function(self):
        """The transfer function relating the input voltage to the output
        voltage."""
        return (self.resistance_bottom
                / (self.resistance_bottom + self.resistance_top))

    def v_in(self, v_out):
        """Given a measured output voltage, returns the calculated input
        voltage.
        """
        return v_out / self.transfer_function

    def v_out(self, v_in):
        """Given an input voltage, returns the calculated output voltage."""
        return v_in * self.transfer_function


class VariableResistanceVoltageDivider(object):
    """A voltage divider where the input voltage is fixed and the output
    resistance is variable. Useful for varistor applications like RTDs.

    Attributes:
        resistance_top: the input resistor for the divider. Units: Ohms.
        input_voltage: the input voltage to the divider. Units: Volts.
    """

    def __init__(self, resistance_top, input_voltage):
        self.resistance_top = resistance_top
        self.input_voltage = input_voltage

    def v_out(self, resistance_bottom):
        """Given an output resistor, calculates the output voltage."""
        transfer_function = (resistance_bottom
                             / (resistance_bottom + self.resistance_top))
        return transfer_function * self.input_voltage

    def resistance_bottom(self, v_out):
        """Given a measured output voltage, calculated the output resistance."""
        transfer_function = v_out / self.input_voltage
        return self.resistance_top / (1.0 / transfer_function - 1.0)
