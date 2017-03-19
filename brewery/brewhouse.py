"""Logic for handling a Brewhouse operations. This includes mashing and boiling.
"""

import logging
import time

from tornado import ioloop

from brewery.pump import SimplePump
from brewery.vessels import HeatExchangedVessel, HeatedVessel
from dsp.state_machine import State
from dsp.state_machine import StateMachine
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

    def __init__(self, client, recipe_instance):
        """Creates the `Brewhouse` instance and waits for a command
        from the webserver to start a new instance.

        Args:
            client: Websocket client for the ManagedVariables.
        """
        LOGGER.info('Initializing Brewery object')
        self.register(client, recipe_instance)

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

        states = [state_prestart, state_premash, state_strike,
                  state_post_strike, state_mash, state_mashout_ramp,
                  state_mashout_recirculation, state_sparge_prep, state_sparge,
                  state_pre_boil, state_mash_to_boil, state_boil_preheat,
                  state_boil, state_cool, state_pumpout]
        self.state = StateMachine(self, states)
        self.state.change_state('state_prestart')
        self.boil_kettle = HeatedVessel(
            rating=5000., volume=5.,
            rtd_params=[0, 0.385, 100.0, 5.0, 0.94, -16.0, 10.], pin=0)
        self.mash_tun = HeatExchangedVessel(
            volume=5., rtd_params=[1, 0.385, 100.0, 5.0, 0.94, -9.0, 10.],
            temperature_source=self.boil_kettle)
        self.main_pump = SimplePump(pin=2)

        self.watch_for_start()

    def register(self, client, recipe_instance):
        """Registers the tracked/managed variables with the recipe
        instance. This allows for the variables to be changed as native
        attributes of the `Brewhouse` and child elements, while
        streaming changes as they happen locally, or receiving changes
        as they happen remotely."""

        self.state.register(recipe_instance)

        # Variables that are @properties and need to be streamed periodically
        # still.
        self.data_streamer.register('boil_kettle__temperature')
        self.data_streamer.register('mash_tun__temperature')
        self.data_streamer.register('boil_kettle__power')
        self.data_streamer.register('system_energy_cost')
        self.data_streamer.register('state__id', 'state')

        # Register normal time series streaming
        Brewhouse.system_energy.register(self, recipe_instance)
        Brewhouse.timer.register(self, recipe_instance)

        # Register sub elements
        self.boil_kettle.register(recipe_instance)
        self.mash_tun.register(recipe_instance)
        self.main_pump.register(recipe_instance)

        def permission_granted(value):
            """If permission is granted, increments the state"""
            if value:
                self.state.id += 1
        Brewhouse.request_permission.register(self, recipe_instance)
        Brewhouse.grant_permission.register(
            self, self.recipe_instance, callback=permission_granted)

    def start_brewing(self):
        """Initializes a new recipe instance on the `Brewhouse`.
        Registers tracked/managed variables with the recipe instance
        assigned to the `Brewhouse`. Initializes all of the states for
        the `Brewhouse`. Schedules the periodic control tasks.
        """
        LOGGER.info('Beginning brewing instance.')



        # Set state machine appropriately
        self.state.change_state('state_prestart')

        # Permission variables
        self.request_permission = False
        self.grant_permission = False

        # Reset energy integrator
        self.system_energy = 0.0

        self.initialize_recipe()

        # Schedule task 1 execution
        self.task1_rate = 1.0 # Seconds
        self.task1_lasttime = time.time()
        self.timer = None
        self.task00()

        self.start_timer()

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

    def end_brewing(self):
        """Terminates a currently running recipe instance on this
        `Brewhouse`. Cancels the task schedules and returns to waiting
        for a new recipe instance to be requested.
        """
        LOGGER.info('Ending brewing instance.')
        self.end_timer()

        self.watch_for_start()
        return

    def start_timer(self):
        """Schedules the control tasks for a new recipe instance on
        this `Brewhouse`.
        """
        self.timers['task00'] = ioloop.PeriodicCallback(
            self.task00, self.task1_rate*1000)
        self.timers['task00'].start()

    def end_timer(self):
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
    def __call__(self):
        LOGGER.debug('In state_prestart')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.request_permission = True


class StatePremash(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self):
        LOGGER.debug('In state_premash')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.strike_temperature)

        if (self.instance.boil_kettle.temperature
                > self.instance.strike_temperature):
            self.instance.request_permission = True


class StateStrike(State):
    """The addition of hot water to the grain."""
    def __call__(self):
        LOGGER.debug('In state_strike')

        self.instance.timer = None

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)

        first_temperature = self.instance.mash_tun.temperature_profile[0][1]
        self.instance.boil_kettle.set_temperature(first_temperature)

        self.instance.request_permission = True


class StatePostStrike(State):
    """Boil element brings water up to strike temperature."""
    def __call__(self):
        LOGGER.debug('In state_post_strike')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)

        first_temperature = self.instance.mash_tun.temperature_profile[0][1]
        self.instance.boil_kettle.set_temperature(first_temperature)

        if (self.instance.boil_kettle.temperature
                > self.instance.mash_tun.temperature_set_point):
            self.instance.request_permission = True


class StateMash(State):
    """Pump turns on and boil element adjusts HLT temp to maintain mash
    temperature.
    """
    def __call__(self):
        LOGGER.debug('In state_mash')

        self.instance.timer = (
            self.instance.state_t0
            + self.instance.mash_tun.temperature_profile_length
            - self.instance.working_time)

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_on()

        self.instance.mash_tun.set_temperature_profile(self.instance.state_t0)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)
        self.instance.timeT0 = time.time()

        if self.instance.timer <= 0.:
            self.instance.state.change_state('state_mashout_ramp')


class StateMashoutRamp(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water
    """
    def __call__(self):
        LOGGER.debug('In state_mashout_ramp')

        self.instance.timer = None

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_on()

        self.instance.mash_tun.set_temperature(
            self.instance.mashout_temperature)
        # Give a little extra push on boil set temp
        self.instance.boil_kettle.set_temperature(
            self.instance.mashout_temperature+5.)

        if (self.instance.boil_kettle.temperature
                > self.instance.mashout_temperature):
            self.instance.state.change_state('state_mashout_recirculation')


class StateMashoutRecirculation(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water this continuation
    just forces an amount of time of mashout at a higher temp of wort.
    """
    def __call__(self):
        LOGGER.debug('In state_mashout_recirculation')

        self.instance.timer = (self.instance.state_t0
                               + self.instance.mashout_time
                               - self.instance.working_time)

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mashout_temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)
        if self.instance.timer <= 0.:
            self.instance.request_permission = True


class StateSpargePrep(State):
    """Prep hoses for sparge process."""
    def __call__(self):
        LOGGER.debug('In state_sparge_prep')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        self.instance.request_permission = True


class StateSparge(State):
    """Slowly puts clean water onto grain bed as it is drained."""
    def __call__(self):
        LOGGER.debug('In state_sparge')

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.timer = None

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        self.instance.request_permission = True


class StatePreBoil(State):
    """Turns off pump to allow switching of hoses for transfer to boil as
    well as boil kettle draining.
    """
    def __call__(self):
        LOGGER.debug('In state_pre_boil')

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.timer = None

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        self.instance.request_permission = True


class StateMashToBoil(State):
    """Turns off boil element and pumps wort from mash tun to the boil kettle.
    """
    def __call__(self):
        LOGGER.debug('In state_mash_to_boil')

        self.instance.timer = None

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        self.instance.request_permission = True


class StateBoilPreheat(State):
    """Heat wort up to temperature before starting to countdown timer in boil.
    """
    def __call__(self):
        LOGGER.debug('In state_boil_preheat')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_temperature)

        preheat_temperature = (self.instance.boil_kettle.temperature_set_point
                               - 10.0)
        if self.instance.boil_kettle.temperature > preheat_temperature:
            self.instance.state.change_state('state_boil')


class StateBoil(State):
    """Boiling to bring temperature to boil temp and maintain temperature for
    duration of boil.
    """
    def __class__(self):
        LOGGER.debug('In state_boil')

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_on()
        self.instance.mash_tun.turn_off()

        self.instance.timer = (self.instance.state_t0
                               + self.instance.boil_time
                               - self.instance.working_time)

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_temperature)
        self.instance.timeT0 = time.time()

        if self.instance.timer <= 0.:
            self.instance.request_permission = True


class StateCool(State):
    """Cooling boil down to pitching temperature."""
    def __call__(self):
        LOGGER.debug('In state_cool')

        self.instance.timer = None

        self.instance.main_pump.turn_off()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        if (self.instance.boil_kettle.temperature
                < self.instance.cool_temperature):
            self.instance.request_permission = True


class StatePumpout(State):
    """Pumping wort out into fermenter."""
    def __call__(self):
        LOGGER.debug('In state_pumpout')

        self.instance.timer = None

        self.instance.main_pump.turn_on()
        self.instance.boil_kettle.turn_off()
        self.instance.mash_tun.turn_off()

        self.instance.mash_tun.set_temperature(
            self.instance.mash_tun.temperature)
        self.instance.boil_kettle.set_temperature(
            self.instance.boil_kettle.temperature)

        self.instance.request_permission = True
