"""Utility functions for interacting with arduino over I2C"""


class AnalogReader(object):
    """Class for reading from an Arduino device over I2C for analog
    measurements.

    Attributes:
        i2c_bus: An i2c bus to be used for communicating with the Arduino. In
            production, usually is an instance of smbus.SMBus.
        address: I2C address for the arduino device on the i2c_bus.
    """

    def __init__(self, i2c_bus, address):
        self.i2c_bus = i2c_bus
        self.address = address

    def read(self, channel):
        """Reads the counts value broadcast from an arduino at the indicated
        channel.

        Args:
            channel: The analog pin to read at.
        """
        self.i2c_bus.write_byte(self.address, channel)

        counts1 = self.i2c_bus.read_byte_data(self.address, 0)
        counts2 = self.i2c_bus.read_byte_data(self.address, 1)
        counts = (counts1 << 8) + counts2
        return counts
