"""Utility functions for interacting with arduino over I2C"""


class AnalogReader(object):
    """Class for reading from an Arduino device over I2C for analog
    measurements.

    Attributes:
        i2c_bus: An i2c bus to be used for communicating with the Arduino. In
            production, usually is an instance of smbus.SMBus.
        address: I2C address for the arduino device on the i2c_bus.
        analog_reference: Voltage reference for the ADC chip on the Arduino.
            Usually 3.3V or 5.0V. Units: Volts.
    """

    def __init__(self, i2c_bus, address, analog_reference):
        self.i2c_bus = i2c_bus
        self.address = address
        self.analog_reference = analog_reference

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

    def read_voltage(self, channel):
        """Reads the voltage at the channel specified from an Arduino at the
        indicated channel.

        Args:
            channel: The analog pin to read at.
        """
        counts = self.read(channel)
        if counts < 0:
            raise RuntimeError(
                "Failed to read data from Arduino on channel {}."
                .format(channel))
        return self.analog_reference * (counts / 1024.0)
