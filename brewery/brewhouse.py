"""Logic for handling a Brewhouse operations. This includes mashing and boiling.
"""

import logging
import time

from tornado import ioloop

from brewery.pump import SimplePump
from brewery.vessels import HeatedVessel
from brewery.vessels import HeatExchangedVessel
from dsp.state_machine import State
from dsp.state_machine import StateMachine
from measurement.gpio import OutputPin
from measurement.rtd_sensor import RtdSensor
from variables import DataStreamer
from variables import StreamingVariable
from variables import SubscribableVariable

LOGGER = logging.getLogger(__name__)


class Brewhouse(object):
    """A top-level class object for operating a brewhouse. Initializes
    communication with the joulia-webserver instance, and manages
    all the equipment associated with the brewhouse system.
    """

    timer = StreamingVariable('timer')
    system_energy = StreamingVariable('system_energy')
    request_permission = StreamingVariable('request_permission')
    grant_permission = SubscribableVariable('grant_permission')

    def __init__(self, client, gpio, recipe_instance):
        """Creates the `Brewhouse` instance and waits for a command
        from the webserver to start a new instance.

        Args:
            client: Websocket client for the ManagedVariables.
        """
        LOGGER.info('Initializing Brewery object')
        self._register(client, recipe_instance)

        self.recipe_instance = recipe_instance
        self.data_streamer = DataStreamer(client, self, recipe_instance, 1000)

        self.strike_temperature = 0.0
        self.mashout_temperature = 0.0
        self.mashout_time = 0.0  # Seconds
        self.boil_temperature = 0.0
        self.boil_time = 0.0  # Seconds
        self.cool_temperature = 0.0
        self.mash_temperature_profile = []

        self.working_time = None
        self.timers = {}
        self.task1_rate = 1.0  # Seconds
        self.task1_lasttime = time.time()

        # Main State Machine Initialization
        self.state = StateMachine(self)
        StatePrestart(self.state)
        StatePremash(self.state)
        StateStrike(self.state)
        StatePostStrike(self.state)
        StateMash(self.state)
        StateMashoutRamp(self.state)
        StateMashoutRecirculation(self.state)
        StateSpargePrep(self.state)
        StateSparge(self.state)
        StatePreBoil(self.state)
        StateMashToBoil(self.state)
        StateBoilPreheat(self.state)
        StateBoil(self.state)
        StateCool(self.state)
        StatePumpout(self.state)
        self.state.id = 0

        boil_sensor_analog_pin = 0
        boil_sensor_rtd_alpha = 0.385
        boil_sensor_rtd_zero_resistance = 100.0
        boil_sensor_analog_reference = 3.3
        boil_sensor_vcc = 3.3
        boil_sensor_tau_filter = 10.0
        boil_sensor_rtd_top_resistance = 1.0E3
        boil_sensor_amplifier_resistor_a = 15.0E3
        boil_sensor_amplifier_resistor_b = 270.0E3
        boil_offset_resistance_bottom = 10.0E3
        boil_offset_resistance_top = 100.0E3
        boil_kettle_temperature_sensor = RtdSensor(
            boil_sensor_analog_pin, boil_sensor_rtd_alpha,
            boil_sensor_rtd_zero_resistance, boil_sensor_analog_reference,
            boil_sensor_vcc, boil_sensor_tau_filter,
            boil_sensor_rtd_top_resistance, boil_sensor_amplifier_resistor_a,
            boil_sensor_amplifier_resistor_b, boil_offset_resistance_bottom,
            boil_offset_resistance_top)

        boil_kettle_heating_element_rating = 5500.0
        boil_kettle_volume = 5.0
        boil_kettle_heating_pin_number = 0
        boil_kettle_heating_pin = OutputPin(
            gpio, boil_kettle_heating_pin_number)
        self.boil_kettle = HeatedVessel(
            client, recipe_instance, boil_kettle_heating_element_rating,
            boil_kettle_volume, boil_kettle_temperature_sensor,
            boil_kettle_heating_pin)

        mash_sensor_analog_pin = 0
        mash_sensor_rtd_alpha = 0.385
        mash_sensor_rtd_zero_resistance = 100.0
        mash_sensor_analog_reference = 3.3
        mash_sensor_vcc = 3.3
        mash_sensor_tau_filter = 10.0
        mash_sensor_rtd_top_resistance = 1.0E3
        mash_sensor_amplifier_resistor_a = 15.0E3
        mash_sensor_amplifier_resistor_b = 270.0E3
        mash_offset_resistance_bottom = 10.0E3
        mash_offset_resistance_top = 100.0E3
        mash_tun_temperature_sensor = RtdSensor(
            mash_sensor_analog_pin, mash_sensor_rtd_alpha,
            mash_sensor_rtd_zero_resistance, mash_sensor_analog_reference,
            mash_sensor_vcc, mash_sensor_tau_filter,
            mash_sensor_rtd_top_resistance, mash_sensor_amplifier_resistor_a,
            mash_sensor_amplifier_resistor_b, mash_offset_resistance_bottom,
            mash_offset_resistance_top)

        mash_tun_volume = 5.0
        mash_temperature_profile = [(60.0, 155.0)]
        self.mash_tun = HeatExchangedVessel(
            client, recipe_instance, mash_tun_volume,
            mash_tun_temperature_sensor,
            temperature_profile=mash_temperature_profile)

        pump_pin_number = 2
        pump_pin = OutputPin(gpio, pump_pin_number)
        self.main_pump = SimplePump(pump_pin)

    def _register(self, client, recipe_instance):
        """Registers the tracked/managed variables with the recipe
        instance. This allows for the variables to be changed as native
        attributes of the `Brewhouse` and child elements, while
        streaming changes as they happen locally, or receiving changes
        as they happen remotely."""

        self.state.register(client, recipe_instance)

        # Variables that are @properties and need to be streamed periodically
        # still.
        self.data_streamer.register('boil_kettle__temperature')
        self.data_streamer.register('mash_tun__temperature')
        self.data_streamer.register('boil_kettle__power')
        self.data_streamer.register('system_energy_cost')
        self.data_streamer.register('state__id', 'state')

        # Register normal time series streaming
        Brewhouse.system_energy.register(client, self, recipe_instance)
        Brewhouse.timer.register(client, self, recipe_instance)

        def permission_granted(value):
            """If permission is granted, increments the state"""
            if value:
                self.state.id += 1
        Brewhouse.request_permission.register(client, self, recipe_instance)
        Brewhouse.grant_permission.register(
            client, self, self.recipe_instance, callback=permission_granted)

    def start_brewing(self):
        """Initializes a new recipe instance on the `Brewhouse`.
        Registers tracked/managed variables with the recipe instance
        assigned to the `Brewhouse`. Initializes all of the states for
        the `Brewhouse`. Schedules the periodic control tasks.
        """
        LOGGER.info('Beginning brewing instance.')

        self.initialize_recipe()

        # Schedule task 1 execution
        self.task1_rate = 1.0  # Seconds
        self.task1_lasttime = time.time()
        self.timer = None

        self.start_timers()

    def initialize_recipe(self):
        """Sets all the temperature profiles and basic recipe settings
        for the current `Brewhouse` instance.
        """
        # Initialize everything
        self.strike_temperature = 162.
        self.mashout_temperature = 170.
        self.mashout_time = 10.*60.  # Seconds
        self.boil_temperature = 217.
        self.boil_time = 60.*60.  # Seconds
        self.cool_temperature = 70.
        self.mash_temperature_profile = [
            [45.*60., 152.0],  # Start at 152
            [15.*60., 155.0],  # At 45min step up to 155
        ]
        self.mash_tun.temperature_profile = self.mash_temperature_profile

    def start_timers(self):
        """Schedules the control tasks for a new recipe instance on
        this `Brewhouse`.
        """
        self.timers['task00'] = ioloop.PeriodicCallback(
            self.task00, self.task1_rate*1000)
        self.timers['task00'].start()

    def cancel_timers(self):
        """Stops all timers/scheduled control tasks."""
        for timer in self.timers.itervalues():
            timer.stop()

    def task00(self):
        """Fast task control execution for the brewhouse system."""
        LOGGER.debug('Evaluating task 00')
        self.working_time = time.time()

        # Evaluate state of controls (mash, pump, boil, etc)
        self.state.evaluate()

        # Check Temperatures
        self.boil_kettle.measure_temperature()
        self.mash_tun.measure_temperature()

        # Controls Calculations for Mash Tun Element
        self.mash_tun.regulate()
        # TODO: (Will) probably need to figure out better option rather than
        # just checking if its Regulator is enabled
        if self.mash_tun.regulator.enabled:
            self.boil_kettle.set_temperature(self.mash_tun.source_temperature)

        # Controls Calculations for Boil Kettle Element
        self.boil_kettle.regulate()

        boil_power = self.boil_kettle.duty_cycle*self.boil_kettle.rating
        delta_time_hours = (self.working_time-self.task1_lasttime)/(60.*60.)
        self.system_energy += boil_power*delta_time_hours

        # Schedule next task 1 event
        self.task1_lasttime = self.working_time


class StatePrestart(State):
    """Everything is off. Waiting for user to initiate process after water
    is filled in the boil kettle/HLT.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_prestart')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.request_permission = True


class StatePremash(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_premash')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.strike_temperature)

        if brewhouse.boil_kettle.temperature > brewhouse.strike_temperature:
            brewhouse.request_permission = True


class StateStrike(State):
    """The addition of hot water to the grain."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_strike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)

        first_temperature = brewhouse.mash_tun.temperature_profile[0][1]
        brewhouse.boil_kettle.set_temperature(first_temperature)

        brewhouse.request_permission = True


class StatePostStrike(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_post_strike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(
            brewhouse.mash_tun.temperature)

        first_temperature = brewhouse.mash_tun.temperature_profile[0][1]
        brewhouse.boil_kettle.set_temperature(first_temperature)

        if (brewhouse.boil_kettle.temperature
                > brewhouse.mash_tun.temperature_set_point):
            brewhouse.request_permission = True


class StateMash(State):
    """Pump turns on and boil element adjusts HLT temp to maintain mash
    temperature.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_mash')

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.mash_tun.temperature_profile_length
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_on()

        brewhouse.mash_tun.set_temperature_profile(brewhouse.state_t0)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)
        brewhouse.timeT0 = time.time()

        if brewhouse.timer <= 0.:
            brewhouse.state.change_state('state_mashout_ramp')


class StateMashoutRamp(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_mashout_ramp')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_on()

        brewhouse.mash_tun.set_temperature(brewhouse.mashout_temperature)
        # Give a little extra push on boil set temp
        brewhouse.boil_kettle.set_temperature(
            brewhouse.mashout_temperature + 5.0)

        if brewhouse.boil_kettle.temperature > brewhouse.mashout_temperature:
            brewhouse.state.change_state('state_mashout_recirculation')


class StateMashoutRecirculation(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water this continuation
    just forces an amount of time of mashout at a higher temp of wort.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_mashout_recirculation')

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.mashout_time
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mashout_temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)
        if brewhouse.timer <= 0.:
            brewhouse.request_permission = True


class StateSpargePrep(State):
    """Prep hoses for sparge process."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_sparge_prep')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateSparge(State):
    """Slowly puts clean water onto grain bed as it is drained."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_sparge')

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.timer = None

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StatePreBoil(State):
    """Turns off pump to allow switching of hoses for transfer to boil as
    well as boil kettle draining.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_pre_boil')

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.timer = None

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateMashToBoil(State):
    """Turns off boil element and pumps wort from mash tun to the boil kettle.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_mash_to_boil')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateBoilPreheat(State):
    """Heat wort up to temperature before starting to countdown timer in boil.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_boil_preheat')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_temperature)

        preheat_temperature = brewhouse.boil_kettle.temperature_set_point - 10.0
        if brewhouse.boil_kettle.temperature > preheat_temperature:
            brewhouse.state.change_state('state_boil')


class StateBoil(State):
    """Boiling to bring temperature to boil temp and maintain temperature for
    duration of boil.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state_boil')

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.boil_time
            - brewhouse.working_time)

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_temperature)
        brewhouse.timeT0 = time.time()

        if brewhouse.timer <= 0.:
            brewhouse.request_permission = True


class StateCool(State):
    """Cooling boil down to pitching temperature."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_cool')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        if brewhouse.boil_kettle.temperature < brewhouse.cool_temperature:
            brewhouse.request_permission = True


class StatePumpout(State):
    """Pumping wort out into fermenter."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state_pumpout')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True
