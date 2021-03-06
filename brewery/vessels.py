"""Classes for representing and interacting with brewing vessels like Boil
Kettles, Mash Tuns, etc.
"""

import logging
import time
from tornado.ioloop import IOLoop

from measurement.gpio import OutputPin
from measurement.rtd_sensor import RtdSensor
from dsp.dsp import Regulator
from utils import power_to_temperature_rate
from variables import OverridableVariable
from variables import StreamingVariable
from variables import SubscribableVariable

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

    emergency_stop = SubscribableVariable('emergency_stop', default=False)
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

    @classmethod
    def from_json(cls, client, gpio, analog_reader, recipe_instance,
                  configuration):
        """Factory for creating a HeatedVessel from JSON configuration."""
        rating = configuration["heating_element"]["rating"]
        volume = configuration["volume"]
        temperature_sensor = RtdSensor.from_json(
            analog_reader, configuration["temperature_sensor"])
        heating_pin = OutputPin(gpio, configuration["heating_element"]["pin"])
        return cls(client, recipe_instance, rating, volume, temperature_sensor,
                   heating_pin)

    def _register(self, client, recipe_instance):
        """Registers this instance with the properties by submitting the
        ``recipe_instance`` to them.

        Args:
            client: The websocket client used for communicated with the server.
            recipe_instance: The id for the recipe instance we are
                connecting with
        """
        HeatedVessel.emergency_stop.register(client, self, recipe_instance)
        HeatedVessel.element_status.register(client, self, recipe_instance)
        HeatedVessel.temperature_set_point.register(
            client, self, recipe_instance)
        HeatedVessel.duty_cycle.register(client, self, recipe_instance)

    def set_temperature(self, value):
        """Sets the temperature set point for the heating element controls.
        """
        LOGGER.debug("Setting temperature %f", value)
        self.temperature_set_point = value

    def disable(self):
        """Disables the heating element on this vessel"""
        LOGGER.debug('Request heated vessel to be disabled.')
        self.element_status = False
        self.heating_pin.set_off()
        self.regulator.disable()

    def enable(self):
        """Turns on the heating element on this vessel. If the emergency stop
        is engaged, call is routed to turn_off instead, which will reset
        regulators as well."""
        LOGGER.debug('Request heated vessel to be enabled.')
        self.element_status = True
        self.regulator.enable()

    def turn_off(self):
        """Turns the heating element pin off. Contrasting with ``turn_on``, it
        does not matter if the element is disabled.
        """
        self.heating_pin.set_off()

    def turn_on(self):
        """Turns the heating element pin on if the element is enabled."""
        if self.emergency_stop:
            LOGGER.info('Emergency stop engaged. Redirecting to turn_off call.')
            self.disable()
            return

        if self.element_status:
            self.heating_pin.set_on()

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

    def regulate(self, this_timer):
        """Executes regulation action to control the temperature of the
        vessel by adjusting the duty_cycle of the heating element.
        """
        LOGGER.debug(
            "Temp: %f, SP: %f", self.temperature, self.temperature_set_point)
        self.duty_cycle = self.regulator.calculate(
            self.temperature, self.temperature_set_point)

        self.schedule_heating_element(this_timer)

    def schedule_heating_element(self, this_timer):
        """Schedules the heating element to turn on and off based off of the
        currently scheduled PeriodicCallback timer and the duty_cycle calculated
        for this heated vessel.

        If the ``duty_cycle * this_timer.callback_time < 1/120``, the element is
        kept off for the entire cycle, since the relay will stay on until the
        next zero crossing which is between 0-1/120 of a second.

        If the ``(1 - duty_cycle) * this_timer.callback_time < 1/120``, the
        element is kept on for the entire cycle, since the relay will stay on
        until the next zero crossing which is between 0-1/120 of a second.

        Returns:
            All timeouts generated.
        """
        timeouts = []
        ioloop = IOLoop.current()
        # TODO(willjschmitt): Figure out way to avoid using protected
        # ``_next_timeout``.
        time_0 = this_timer._next_timeout  # pylint: disable=protected-access
        if self.duty_cycle * this_timer.callback_time < (1.0 / 120.0):
            timeouts.append(ioloop.call_at(time_0, self.turn_off))
        elif (1.0 - self.duty_cycle) * this_timer.callback_time < (1.0 / 120.0):
            timeouts.append(ioloop.call_at(time_0, self.turn_on))
        else:
            off_time = time_0 + self.duty_cycle * this_timer.callback_time
            turn_on = ioloop.call_at(time_0, self.turn_on)
            turn_off = ioloop.call_at(off_time, self.turn_off)
            timeouts.append(turn_on)
            timeouts.append(turn_off)
        return timeouts

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
        return power_to_temperature_rate(net_power, self.volume)


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

    emergency_stop = SubscribableVariable('emergency_stop', default=False)
    temperature_set_point = OverridableVariable(
        'mash_tun__temperature_set_point')

    # TODO(willjschmitt): Make heat_exchanger_conductivity a required arg.
    def __init__(self, client, recipe_instance, volume, temperature_sensor,
                 heat_exchanger_conductivity=1.0):
        super(HeatExchangedVessel, self).__init__(volume, temperature_sensor)
        self._register(client, recipe_instance)

        self.heat_exchanger_conductivity = heat_exchanger_conductivity

        self.temperature_set_point = 0.
        self.source_temperature = self.temperature_set_point

        gain_proportional = None
        gain_integral = None
        self.regulator = Regulator(time, gain_proportional, gain_integral,
                                   max_output=15.0, min_output=-15.0)
        self.recalculate_gains()

        self.enabled = False

    @classmethod
    def from_json(cls, client, analog_reader, recipe_instance,
                  configuration):
        """Factory for creating a HeatExchangedVessel from JSON configuration.
        """
        volume = configuration["volume"]
        heat_exchanger_conductivity \
            = configuration["heat_exchanger_conductivity"]
        temperature_sensor = RtdSensor.from_json(
            analog_reader, configuration["temperature_sensor"])
        return cls(client, recipe_instance, volume, temperature_sensor,
                   heat_exchanger_conductivity=heat_exchanger_conductivity)

    def _register(self, client, recipe_instance):
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

    def disable(self):
        """Disables the pump on this vessel along with its controls"""
        self.enabled = False
        self.regulator.disable()

    def enable(self):
        """Turns on the pump for this vessel along with its controls"""
        if self.emergency_stop:
            LOGGER.info('Emergency stop engaged. Redirecting to turn_off call.')
            self.disable()
            return
        self.enabled = True
        self.regulator.enable()

    def set_temperature(self, temperature):
        """Sets the temperatures setpoint for the Regulator to control
        the vessel temperature.
        """
        self.temperature_set_point = temperature

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
        if not self.enabled:
            return 0.0

        # TODO(will): Add energy loss to environment.
        delta_temperature = self.source_temperature - self.temperature
        net_power = delta_temperature * self.heat_exchanger_conductivity
        return power_to_temperature_rate(net_power, self.volume)
