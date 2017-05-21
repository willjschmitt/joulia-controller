"""Readers for measuring analog values from SPI/I2C peripheral devices like an
Arduino or MCP3004/8.
"""


class AnalogReaderBase(object):
    """Abstract base class for Analog Readers measuring an analog voltage on an
    I2C or SPI Bus.

    Attributes:
        counts_reference: The max number of counts the reader uses for a value
            corresponding to the analog_reference.
        analog_reference: Voltage reference for the ADC chip on the Arduino.
            Usually 3.3V or 5.0V. Units: Volts.
    """
    def __init__(self, counts_reference, analog_reference):
        self.counts_reference = counts_reference
        self.analog_reference = analog_reference

    def read(self, channel):
        """Reads the counts value broadcast from a slave device at the indicated
        channel.

        Args:
            channel: The analog pin to read at.
        """
        raise NotImplementedError()

    def read_voltage(self, channel):
        """Reads the voltage at the channel specified from an Arduino at the
        indicated channel.

        Args:
            channel: The analog pin to read at.
        """
        counts = self.read(channel)
        if counts < 0:
            raise RuntimeError(
                "Failed to read data on channel {}.".format(channel))
        return self.analog_reference * (counts / self.counts_reference)


class ArduinoAnalogReader(AnalogReaderBase):
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
        counts_reference = 1024.0
        super(ArduinoAnalogReader, self).__init__(counts_reference,
                                                  analog_reference)
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


class MCP3004AnalogReader(AnalogReaderBase):
    """Reader for an MCP3004 over SPI for analog measurements.

   Attributes:
       mcp: The MCP3004 device as an MCP3008 instance from the Adafruit_MCP3008
           library.
       analog_reference: Voltage reference for the ADC chip on the Arduino.
           Usually 3.3V or 5.0V. Units: Volts.
   """

    def __init__(self, mcp, analog_reference):
        counts_reference = 1024.0
        super(MCP3004AnalogReader, self).__init__(counts_reference,
                                                  analog_reference)
        self.mcp = mcp

    def read(self, channel):
        """Reads the counts value broadcast from an MCP3004 at the indicated
        channel.

        Args:
            channel: The analog pin to read at.
        """
        return self.mcp.read_adc(channel)
