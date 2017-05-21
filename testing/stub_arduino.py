"""Stubs for the AnalogReader in measurement.arduino."""

from measurement.arduino import AnalogReader


class StubAnalogReader(AnalogReader):
    """Stub for the AnalogReader."""
    def __init__(self, i2c_bus, address, analog_reference):
        super(StubAnalogReader, self).__init__(i2c_bus, address,
                                               analog_reference)
        self.counts = 0

    def read(self, channel):
        return self.counts
