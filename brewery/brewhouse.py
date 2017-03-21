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

    def __init__(self, client, gpio, analog_reader, recipe_instance,
                 boil_kettle, mash_tun, main_pump):
        """Creates the `Brewhouse` instance and waits for a command
        from the webserver to start a new instance.

        Args:
            client: Websocket client for the ManagedVariables.
        """
        LOGGER.info('Initializing Brewery object')
        self._register(client, recipe_instance)

        self.recipe_instance = recipe_instance
        self.boil_kettle = boil_kettle
        self.mash_tun = mash_tun
        self.main_pump = main_pump

        self.data_streamer = DataStreamer(client, self, recipe_instance, 1000)
        self._initialize_data_streamer()

        self.strike_temperature = 0.0
        self.mashout_temperature = 0.0
        self.mashout_time = 0.0  # Seconds
        self.boil_temperature = 0.0
        self.boil_time = 0.0  # Seconds
        self.cool_temperature = 0.0
        self.mash_temperature_profile = []
        self.system_energy = 0.0

        self.working_time = None
        self.timers = {}
        self.task1_rate = 1.0  # Seconds
        self.task1_lasttime = time.time()

        # Main State Machine Initialization
        self.state = StateMachine(self)
        self.state.register(client, recipe_instance)
        self._initialize_state_machine()

    def _register(self, client, recipe_instance):
        """Registers the tracked/managed variables with the recipe
        instance. This allows for the variables to be changed as native
        attributes of the `Brewhouse` and child elements, while
        streaming changes as they happen locally, or receiving changes
        as they happen remotely.
        """
        # Register normal time series streaming
        Brewhouse.system_energy.register(client, self, recipe_instance)
        Brewhouse.timer.register(client, self, recipe_instance)

        def permission_granted(value):
            """If permission is granted, increments the state"""
            if value:
                self.state.id += 1
        Brewhouse.request_permission.register(client, self, recipe_instance)
        Brewhouse.grant_permission.register(
            client, self, recipe_instance, callback=permission_granted)

    def _initialize_state_machine(self):
        """Initializes state machine into fully populated state. Should be
        called by __init__.
        """
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

    def _initialize_data_streamer(self):
        """Registers variables that are @properties and need to be streamed
        periodically still.
        """
        self.data_streamer.register('boil_kettle__temperature')
        self.data_streamer.register('mash_tun__temperature')
        self.data_streamer.register('boil_kettle__power')
        self.data_streamer.register('system_energy_cost')
        self.data_streamer.register('state__id', 'state')

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
        for timer in self.timers.values():
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
        seconds_per_hours = 60.0 * 60.0
        delta_time_seconds = self.working_time - self.task1_lasttime
        delta_time_hours = delta_time_seconds / seconds_per_hours
        self.system_energy += boil_power*delta_time_hours

        # Schedule next task 1 event
        self.task1_lasttime = self.working_time

    @property
    def state_t0(self):
        return self.state.state_time_change


class StatePrestart(State):
    """Everything is off. Waiting for user to initiate process after water
    is filled in the boil kettle/HLT.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state Prestart')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.request_permission = True


class StatePremash(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state Premash')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.strike_temperature)

        if brewhouse.boil_kettle.temperature > brewhouse.strike_temperature:
            brewhouse.request_permission = True
        else:
            brewhouse.request_permission = False


class StateStrike(State):
    """The addition of hot water to the grain."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state Strike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        first_temperature = brewhouse.mash_tun.temperature_profile[0][1]
        brewhouse.boil_kettle.set_temperature(first_temperature)

        brewhouse.request_permission = True


class StatePostStrike(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state PostStrike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(
            brewhouse.mash_tun.temperature)

        first_temperature = brewhouse.mash_tun.temperature_profile[0][1]
        brewhouse.boil_kettle.set_temperature(first_temperature)

        if (brewhouse.boil_kettle.temperature
                > brewhouse.boil_kettle.temperature_set_point):
            brewhouse.request_permission = True
        else:
            brewhouse.request_permission = False


class StateMash(State):
    """Pump turns on and boil element adjusts HLT temp to maintain mash
    temperature.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state Mash')

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.mash_tun.temperature_profile_length
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_on()

        brewhouse.mash_tun.set_temperature_profile(brewhouse.state_t0)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        if brewhouse.timer <= 0.:
            self.state_machine.next_state()


class StateMashoutRamp(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state MashoutRamp')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_on()

        brewhouse.mash_tun.set_temperature(brewhouse.mashout_temperature)
        # Give a little extra push on boil set temp
        brewhouse.boil_kettle.set_temperature(
            brewhouse.mashout_temperature + 5.0)

        if brewhouse.boil_kettle.temperature > brewhouse.mashout_temperature:
            self.state_machine.next_state()


class StateMashoutRecirculation(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water this continuation
    just forces an amount of time of mashout at a higher temp of wort.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state MashoutRecirculation')

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.mashout_time
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mashout_temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.mashout_temperature)
        if brewhouse.timer <= 0.:
            brewhouse.request_permission = True
        else:
            brewhouse.request_permission = False


class StateSpargePrep(State):
    """Prep hoses for sparge process."""
    def __call__(self, brewhouse):
        LOGGER.debug('In state SpargePrep')

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
        LOGGER.debug('In state Sparge')

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
        LOGGER.debug('In state PreBoil')

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
        LOGGER.debug('In state MashToBoil')

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
        LOGGER.debug('In state BoilPreheat')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.turn_on()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_temperature)

        preheat_temperature = brewhouse.boil_kettle.temperature_set_point - 10.0
        if brewhouse.boil_kettle.temperature > preheat_temperature:
            self.state_machine.next_state()


class StateBoil(State):
    """Boiling to bring temperature to boil temp and maintain temperature for
    duration of boil.
    """
    def __call__(self, brewhouse):
        LOGGER.debug('In state Boil')

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
        LOGGER.debug('In state Cool')

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
        LOGGER.debug('In state Pumpout')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.turn_off()
        brewhouse.mash_tun.turn_off()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True
