"""Stubs for the AnalogReader in measurement.arduino."""

from measurement.analog_reader import AnalogReaderBase


class StubAnalogReader(AnalogReaderBase):
    """Stub for the AnalogReader."""
    def __init__(self):
        # Since we are overriding read_voltage, the counts_reference does not
        # matter, nor does the analog_reference. We return the voltage set
        # directly.
        counts_reference = None
        analog_reference = None
        super(StubAnalogReader, self).__init__(counts_reference,
                                               analog_reference)
        self.voltage = 0.0

    def read_voltage(self, channel):
        return self.voltage
