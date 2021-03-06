"""RTD Sensor module for resistance temperature devices"""

import logging
import time

from dsp.dsp import FirstOrderLag
from measurement.circuits import VariableResistanceVoltageDivider
from measurement.circuits import VoltageDivider
from measurement.op_amp import DifferentialAmplifier
from measurement.op_amp import VoltageFollower


LOGGER = logging.getLogger(__name__)


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
        analog_reader: The AnalogReader object used for requesting analog
            measurements from.
        analog_in_pin: The analog in pin on the arduino pin, where the
            voltage measurement should be made from the RTD amplifier circuit
        alpha: The temperature coefficient of the RTD (Ohm/(Ohm*degC)).
            alpha is defined as (resistance @ 100degC- resistance @ 0degC)
            / (100 * resistance @ 100degC)
        zero_resistance: The resistance of the tem
        analog_reference_voltage: Reference voltage for the ADC
            measurement as set on the Arduino.
        scale: Multiplier on the measured temperature (degF/degF) for
            calibration.
        offset: Linear shift/offset on the measured temperature
            (in degF) for calibration
        tau: First order low pass filter time constant to remove high
            frequency noise from circuit measurement
        amplifier: The differential amplifier amplifying the measured voltage.
        offset_follower: The voltage follower for voltage offset.
        offset_divider: The voltage divider generating the voltage offset.
        rtd_follower: The voltage follower for the rtd input.
        rtd_divider: The voltage divider generating a signal voltage from the
            RTD.
        temperature_unfiltered: The unfiltered raw temperature measured from
            the RTD.
    """

    def __init__(self, analog_reader, analog_pin, alpha, zero_resistance,
                 analog_reference_voltage, tau, vcc, resistance_rtd_top,
                 amplifier_resistance_a, amplifier_resistance_b,
                 offset_resistance_bottom, offset_resistance_top, scale=1.0,
                 offset=0.0):
        """Constructor

        Args:
            vcc: The voltage input to the amplifier circuit, used for
                reference, from the Arduino (Volts)
            amplifier_resistance_a: The resistance that serves as the
                denominator in the gain of the difference amplifier (Ohms)
            amplifier_resistance_b: The resistance that serves as the
                numerator in the gain of the difference amplifier (Ohms)
            offset_resistance_bottom: The resistance in the bottom of the
                voltage divider for the offset voltage follower circuit (Ohms)
            offset_resistance_top: The resistance in the top of the
                voltage divider for the offset voltage follower circuit (Ohms)
        """
        self.analog_reader = analog_reader

        self.temperature_filter = FirstOrderLag(time, tau)

        self.analog_in_pin = analog_pin
        self.analog_reference_voltage = analog_reference_voltage

        self.alpha = alpha
        self.zero_resistance = zero_resistance

        self.scale = scale
        self.offset = offset

        self.amplifier = DifferentialAmplifier(
            amplifier_resistance_a, amplifier_resistance_b)

        self.offset_follower = VoltageFollower()
        self.offset_divider = VoltageDivider(
            offset_resistance_top, offset_resistance_bottom)

        self.rtd_follower = VoltageFollower()
        self.rtd_divider = VariableResistanceVoltageDivider(
            resistance_rtd_top, vcc)

        self.vcc = vcc

        self.temperature_unfiltered = 0.0

    @classmethod
    def from_json(cls, analog_reader, configuration):
        """Factory for creating a RtdSensor from JSON configuration."""
        analog_pin = configuration["analog_pin"]
        alpha = configuration["rtd"]["alpha"]
        zero_resistance = configuration["rtd"]["zero_resistance"]
        analog_reference_voltage = configuration["analog_reference"]
        tau = configuration["tau_filter"]
        vcc = configuration["amplifier"]["vcc"]
        resistance_rtd_top = configuration["amplifier"]["rtd_top_resistance"]
        amplifier_resistance_a \
            = configuration["amplifier"]["amplifier_resistance_a"]
        amplifier_resistance_b \
            = configuration["amplifier"]["amplifier_resistance_b"]
        offset_resistance_bottom \
            = configuration["amplifier"]["offset_resistance_bottom"]
        offset_resistance_top \
            = configuration["amplifier"]["offset_resistance_top"]
        return cls(analog_reader, analog_pin, alpha, zero_resistance,
                   analog_reference_voltage, tau, vcc, resistance_rtd_top,
                   amplifier_resistance_a, amplifier_resistance_b,
                   offset_resistance_bottom, offset_resistance_top)

    @property
    def temperature(self):
        """Filtered temperature measured from the RTD amplifier circuit."""
        return self.temperature_filter.filtered

    def measure(self):
        """Samples the voltage from the RTD amplifier circuit and calculates
        the temperature. Applies the filter calculation to newly sampled
        temperature.
        """
        voltage_measured = self.analog_reader.read_voltage(self.analog_in_pin)

        # Back out the voltage at the RTD based on the amplifier circuit
        voltage_rtd = (-self.amplifier.v_in(voltage_measured)
                       + self.offset_divider.v_out(self.vcc))

        resistance_rtd = self.rtd_divider.resistance_bottom(voltage_rtd)

        temperature = self._resistance_to_temperature(resistance_rtd)

        # Add calibration scaling and offset
        temperature_calibrated = (temperature * self.scale) + self.offset

        self.temperature_unfiltered = temperature_calibrated
        self.temperature_filter.filter(temperature_calibrated)

    def reverse_temperature(self, temperature):
        """In an simulated system provides the voltage the RTD needs to measure.

        Converts temperature back to ADC input voltage, which can be applied to
        a mocked analog reader in simulations.

        Does not modify any internal state.

        Attributes:
            temperature: Temperature to calculate counts for.

        Returns:
            Voltage the ADC would need to receive to measure the provided
            temperature.
        """
        resistance_rtd = self.temperature_to_resistance(temperature)

        voltage_rtd = self.rtd_divider.v_out(resistance_rtd)

        voltage_measured = self.amplifier.v_out(
            self.offset_divider.v_out(self.vcc) - voltage_rtd)

        LOGGER.debug(
            "resistance_rtd: %s; voltage_rtd: %s, voltage_measured: %s",
            resistance_rtd, voltage_rtd, voltage_measured)
        return voltage_measured

    def _resistance_to_temperature(self, resistance):
        """Converts RTD resistance into a temperature. Units: Fahrenheit. Uses
        a simple linear approximation rather than a full Callendar-Van Dusen.
        """
        # Convert resistance into temperature
        temperature_celsius = ((resistance - self.zero_resistance)
                               / (self.alpha * self.zero_resistance))
        return celsius_to_fahrenheit(temperature_celsius)

    def temperature_to_resistance(self, temperature_fahrenheit):
        """Converts temperature into an RTD resistance.

        Uses a simple linear approximation rather than a full Callendar-Van
        Dusen.

        Arguments:
            temperature_fahrenheit: The temperature (in fahrenheit) to calculate
                the RTD resistance for.

        Returns:
            Resistance in Ohms the RTD would be at the provided temperature.
        """
        temperature_celsius = fahrenheit_to_celsius(temperature_fahrenheit)

        resistance = (
            (temperature_celsius * (self.alpha * self.zero_resistance))
            + self.zero_resistance)
        return resistance


def celsius_to_fahrenheit(degrees_celsius):
    """Converts a temperature from celsius to fahrenheit."""
    return degrees_celsius * (9.0/5.0) + 32.0


def fahrenheit_to_celsius(degrees_fahrenheit):
    """Converts a temperature from fahrenheit to celsius."""
    return (degrees_fahrenheit - 32.0) * (5.0/9.0)
