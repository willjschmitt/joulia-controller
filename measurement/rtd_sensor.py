from dsp.first_order_lag import FirstOrderLag

class RtdSensor(object):
    """A resistance temperature device that measures temperature by
    a measuring the voltage across the RTD in a voltage divider circuit,
    which is then amplified into an analog to digital converter (ADC) chip.

    Obtains the analog voltage measurement from an Arduino device connected
    on the I2C bus, with the amplifier circuit output connected to
    ``analog_in_pin``.

    See also: https://en.wikipedia.org/wiki/Resistance_thermometer

    Amplifier circuit roughly follows concept found at
    https://openenergymonitor.org/emon/buildingblocks/rtd-temperature-sensing,
    which includes three Op-Amp circuits: one following the RTD voltage,
    one following a voltage divider to give a reference voltage, and then
    calculating the difference between these voltages with a gain. This
    serves to optimize the resolution of the voltage measurement over the
    useful, realistic range for measuring voltage.

    Attributes:
        analog_in_pin - The analog in pin on the arduino pin, where the
            voltage measurement should be made from the RTD amplifier circuit
        alpha - The temperature coefficient of the RTD (Ohm/(Ohm*degC)).
            alpha is defined as (resistance @ 100degC- resistance @ 0degC)
            / (100 * resistance @ 100degC)
        zero_resistance - The resistance of the tem
        analog_reference_voltage - Reference voltage for the ADC
            measurement as set on the Arduino.
        scale - Multiplier on the measured temperature (degF/degF) for
            calibration
        offset - Linear shift/offset on the measured temperature
            (in degF) for calibration
        tau - First order low pass filter time constant to remove high
            frequency noise from circuit measurement
        amplifier_gain - The multiplicative gain calculated from the
            resistances in the difference op amp circuit
        voltage_offset - The voltage offset going into the difference
            op amp circuit based on the resistances in the voltage divider
            and the input reference voltage from the arduino
        resistance_rtd_top - The resistance of the top section of the
            voltage divider containing the RTD (Ohms)
    """
    def __init__(self, analog_pin, alpha, zero_resistance,
                 analog_reference_voltage,
                 scale=1.0, offset=0.0,
                 tau=10.0,
                 vcc=5.0,
                 resistance_rtd_top = 1.0E3,
                 amplifier_resistance_a=15.0E3,amplifier_resistance_b=270.0E3,
                 offset_resistance_bottom=10.0E3,offset_resistance_top = 100.0E3):
        """Constructor

        Args:
            vcc - The voltage input to the amplifier circuit, used for
                reference, from the Arduino (Volts)
            amplifier_resistance_a - The resistance that serves as the
                denominator in the gain of the difference amplifier (Ohms)
            amplifier_resistance_b - The resistance that serves as the
                numerator in the gain of the difference amplifier (Ohms)
            offset_resistance_bottom - The resistance in the bottom of the
                voltage divider for the offset voltage follower circuit (Ohms)
            offset_resistance_top - The resistance in the top of the
                voltage divider for the offset voltage follower circuit (Ohms)
        """
        self.temperature_filter = FirstOrderLag(tau)

        self.analog_in_pin = analog_pin
        self.analog_reference_voltage = analog_reference_voltage

        self.alpha = alpha
        self.zero_resistance = zero_resistance

        self.scale = scale
        self.offset = offset

        self.resistance_rtd_top = resistance_rtd_top

        self.amplifier_gain = amplifier_resistance_a/amplifier_resistance_b

        offset_ratio = (offset_resistance_bottom
                        / (offset_resistance_top + offset_resistance_bottom))
        self.voltage_offset = vcc * offset_ratio

        self.vcc = vcc

    @property
    def temperature(self):
        """Filtered temperature measured from the RTD amplifier circuit."""
        return self.temperature_filter.filtered

    def measure(self):
        """Samples the voltage from the RTD amplifier circuit and calculates
        the temperature. Applies the filter calculation to newly sampled
        temperature.
        """
        # Measured voltage into Arduino
        counts = 1000 #arduino_analogRead(fd, analog_in_pin);
        if counts < 0:
            return
        voltage_measured = self.analog_reference_voltage * (counts/1024.)

        # Back out the voltage at the RTD based on the amplifier circuit
        voltage_rtd = voltage_measured * self.amplifier_gain + self.voltage_offset

        resistance_rtd = voltage_rtd * self.resistance_rtd_top / (self.vcc - voltage_rtd)

        # Convert resistance into temperature
        temperature_celsius = (resistance_rtd - 100.0)/self.alpha
        temperature = celsius_to_fahrenheit(temperature_celsius)

        # Add calibration scaling and offset
        temperature *= self.scale
        temperature += self.offset

        self.temperature_filter.filter(temperature)

def celsius_to_fahrenheit(degrees_celsius):
    """Converts a temperature from celsius to fahrenheit"""
    return degrees_celsius * (9.0/5.0) + 32.0
