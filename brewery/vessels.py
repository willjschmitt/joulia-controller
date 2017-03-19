"""Classes for representing and interacting with brewing vessels like Boil
Kettles, Mash Tuns, etc.
"""

import logging
import time

from dsp.dsp import Integrator
from dsp.dsp import Regulator
from measurement.rtd_sensor import RtdSensor
from variables import OverridableVariable
from variables import StreamingVariable

LOGGER = logging.getLogger(__name__)


class SimpleVessel(object):
    """An abstract class to represent a vessel that contains liquid.

    Attributes:
        volume: Volume of liquid that is in the vessel. Units: gallons.
    """
    def __init__(self, volume):
        self.volume = volume

    def set_liquid_level(self, volume):
        """Changes the current liquid level of the vessel.

        Args:
            volume: The volume now in the vessel.
        """
        self.volume = volume


class TemperatureMonitoredVessel(SimpleVessel):
    """A vessel that has a temperature sensor monitoring the temperature
    of the liquid it contains.

    Attributes:
        temperature_sensor: an RtdSensor object to retrieve measurements from
    """

    def __init__(self, volume, temperature_sensor):
        super(TemperatureMonitoredVessel, self).__init__(volume)

        self.temperature_sensor = temperature_sensor

    @property
    def temperature(self):
        """Gets the current temperature of the vessel."""
        return self.temperature_sensor.temperature

    def measure_temperature(self):
        """Samples the temperature from the measurement circuit."""
        return self.temperature_sensor.measure()


class HeatedVessel(TemperatureMonitoredVessel):
    """A vessel with temperature monitoring and a heating method"""

    temperature_set_point = OverridableVariable(
        'boil_kettle__temperature_set_point', default=0.)
    element_status = OverridableVariable(
        'boil_kettle__element_status', default=False)
    duty_cycle = StreamingVariable('boil_kettle__duty_cycle')

    def __init__(self, client, recipe_instance,
                 rating, volume, temperature_sensor, heating_pin):
        super(HeatedVessel, self).__init__(volume, temperature_sensor)
        self._register(client, recipe_instance)

        self.rating = rating  # Watts (heating element)
        self.heating_pin = heating_pin

        self.temperature_set_point = 0.0
        self.duty_cycle = 0.0
        self.duty_period = 1.0  # Seconds

        # No gains at first. Just need to set them before calculating them.
        gain_proportional = None
        gain_integral = None
        self.regulator = Regulator(time, gain_proportional, gain_integral,
                                   max_output=1.0, min_output=0.0)
        self.recalculate_gains()

    def _register(self, client, recipe_instance):
        """Registers this instance with the properties by submitting the
        ``recipe_instance`` to them.

        Args:
            client: The websocket client used for communicated with the server.
            recipe_instance: The id for the recipe instance we are
                connecting with
        """
        HeatedVessel.element_status.register(client, self, recipe_instance)
        HeatedVessel.temperature_set_point.register(
            client, self, recipe_instance)
        HeatedVessel.duty_cycle.register(client, self, recipe_instance)

    def set_temperature(self, value):
        """Sets the temperature set point for the heating element controls.
        """
        LOGGER.debug("Setting temperature %f", value)
        self.temperature_set_point = value

    def turn_off(self):
        """Disables the heating element on this vessel"""
        LOGGER.debug('Request heated vessel turn off.')
        self.element_status = False
        self.heating_pin.set_off()
        self.regulator.disable()

    def turn_on(self):
        """Turns off the heating element on this vessel"""
        LOGGER.debug('Request heated vessel turn on.')
        self.element_status = True
        self.heating_pin.set_on()
        self.regulator.enable()

    def set_liquid_level(self, volume):
        """Adjusts the liquid volume of the vessel, which then recalculates
        the control gains based on the new liquid volume.
        """
        super(HeatedVessel, self).set_liquid_level(volume)
        self.recalculate_gains()

    def recalculate_gains(self):
        """Calculates control gains based on the amount of liquid and
        heating rating of the heating element
        """
        self.regulator.gain_proportional = 10.0 * (self.volume / self.rating)
        self.regulator.gain_integral = 100.0 * (self.volume / self.rating)

    def regulate(self):
        """Executes regulation action to control the temperature of the
        vessel by adjusting the duty_cycle of the heating element.
        """
        LOGGER.debug(
            "Temp: %f, SP: %f", self.temperature, self.temperature_set_point)
        self.duty_cycle = self.regulator.calculate(
            self.temperature, self.temperature_set_point)

    @property
    def power(self):
        """A calculated power injected into the vessel by the heating element
        based on the duty cycle and rating.
        """
        return self.duty_cycle * self.rating * self.element_status

    @property
    def temperature_ramp(self):
        """An estimated degF/sec rate of change of liquid based on ideal
        conditions. Does not include ambient losses.
        """
        # TODO(will): Calculate energy loss to environment.
        net_power = self.power
        volume = self.volume * 3.79  # L
        density_water = 1000.0  # grams/L
        mass = volume * density_water  # grams
        specific_heat_water = 4.184  # J/(degC * grams)
        specific_heat = mass * specific_heat_water  # J/degC
        specific_heat_fahrenheit = specific_heat * (5.0 / 9.0)  # J/degF
        return net_power / specific_heat_fahrenheit  # degF/second


class HeatExchangedVessel(TemperatureMonitoredVessel):
    """A vessel that can be heated by by a slow heat-exchanged process,
    which includes flow as a controllable parameter.

    Attributes:
        source_temperature: The temperature setpoint for our heat exchanger
            source. If this is a Mash Tun, for example, this would be the boil
            kettle temperature set point.
        heat_exchanger_conductivity: Represents rate of heat exchange between
            source liquid and target liquid as W/(delta degF).
    """

    temperature_set_point = OverridableVariable(
        'mash_tun__temperature_set_point')

    def __init__(self, client, recipe_instance, volume, temperature_sensor,
                 heat_exchanger_conductivity=1.0, temperature_profile=None):
        super(HeatExchangedVessel, self).__init__(volume, temperature_sensor)
        self.register(client, recipe_instance)

        self.heat_exchanger_conductivity = heat_exchanger_conductivity
        self.temperature_profile = temperature_profile

        self.temperature_set_point = 0.
        self.source_temperature = self.temperature_set_point

        gain_proportional = None
        gain_integral = None
        self.regulator = Regulator(time, gain_proportional, gain_integral,
                                   max_output=15.0, min_output=-15.0)
        self.recalculate_gains()

        self.enabled = False

    def register(self, client, recipe_instance):
        HeatExchangedVessel.temperature_set_point.register(
            client, self, recipe_instance)

    def recalculate_gains(self):
        """Calculates control gains based on the amount of liquid and
        heating rating of the heating element.
        """
        self.regulator.gain_proportional = (
            0.2 * (self.volume / self.heat_exchanger_conductivity))
        self.regulator.gain_integral = (
            0.002 * (self.volume / self.heat_exchanger_conductivity))

    def turn_off(self):
        """Disables the pump on this vessel along with its controls"""
        self.enabled = False
        self.regulator.disable()

    def turn_on(self):
        """Turns on the pump for this vessel along with its controls"""
        self.enabled = True
        self.regulator.enable()

    def set_temperature(self, temperature):
        """Sets the temperatures setpoint for the Regulator to control
        the vessel temperature.
        """
        self.temperature_set_point = temperature

    def _absolute_temperature_profile(self):
        """Creates a temperature profile where the times are relative to start
        rather than the lengths of time for each segment. An additional segment
        at the end is added with None for the temperature, indicating the end.

        That is, `[(15.0, 150.), (15.0, 155.0)]` becomes
        `[(0.0, 150.0), (15.0, 155.0), (30.0, None)]`.
        """
        profile = [(0.0, self.temperature_profile[0][1])]
        for i, point in enumerate(self.temperature_profile):
            time_sum = profile[-1][0] + point[0]
            if i+1 == len(self.temperature_profile):
                next_temperature = None
            else:
                next_temperature = self.temperature_profile[i+1][1]
            profile.append((time_sum, next_temperature))
        return profile

    def set_temperature_profile(self, time_in_profile):
        """Sets the temperature setpoint for the controls based on the
        current time relative to the start of the temperature profile.

        Args:
            time_in_profile: The time to reference as the beginning of the
                profile.
        """
        assert self.temperature_profile is not None

        absolute_temperature_profile = self._absolute_temperature_profile()
        assert time_in_profile >= absolute_temperature_profile[0][0]
        assert time_in_profile < absolute_temperature_profile[-1][0]

        for point in reversed(absolute_temperature_profile):
            if time_in_profile >= point[0]:
                self.set_temperature(point[1])
                return

    @property
    def temperature_profile_length(self):
        """The total amount of time prescribed in the ``temperature_profile``
        """
        absolute_profile = self._absolute_temperature_profile()
        return absolute_profile[-1][0]

    def set_liquid_level(self, volume):
        """Adjusts the liquid volume of the vessel, which then recalculates
        the control gains based on the new liquid volume.
        """
        self.volume = volume
        self.recalculate_gains()

    def regulate(self):
        """Executes regulation action to control the temperature of the
        vessel by adjusting the temperature set point of the vessel serving
        as the heat source.
        """
        regulator_temperature = self.regulator.calculate(
            self.temperature, self.temperature_set_point)
        self.source_temperature = self.temperature + regulator_temperature

    @property
    def temperature_ramp(self):
        """An estimated degF/sec rate of change of liquid based on ideal
        conditions. Does not include ambient losses.
        """
        # TODO(will): Add energy loss to environment.
        if self.enabled:
            delta_temperature = self.source_temperature - self.temperature
            net_power = delta_temperature * self.heat_exchanger_conductivity
            volume = self.volume * 3.79  # L
            density_water = 1000.0  # grams/L
            mass = volume * density_water  # grams
            specific_heat_water = 4.184  # J/(degC * grams)
            specific_heat = mass * specific_heat_water  # J/degC
            specific_heat_fahrenheit = specific_heat * (5.0 / 9.0)  # J/degF
            return net_power / specific_heat_fahrenheit  # degF/second
        else:
            return 0.0
