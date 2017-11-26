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

    def __init__(self, client, recipe_instance, boil_kettle, mash_tun,
                 main_pump, recipe):
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

        self.recipe = recipe
        self.system_energy = 0.0

        self.working_time = None
        self.timers = {}
        self.task1_rate = 1.0  # Seconds
        self.task1_lasttime = time.time()

        # Main State Machine Initialization
        self.state = StateMachine(self, client, recipe_instance)
        self._initialize_state_machine()

    @classmethod
    def from_json(cls, client, gpio, analog_reader, recipe_instance, recipe,
                  configuration):
        """Factory for creating a Brewhouse from JSON configuration."""
        boil_kettle = HeatedVessel.from_json(
            client, gpio, analog_reader, recipe_instance,
            configuration["boil_kettle"])
        mash_tun = HeatExchangedVessel.from_json(
            client, analog_reader, recipe_instance, configuration["mash_tun"])
        main_pump = SimplePump.from_json(
            client, gpio, recipe_instance, configuration["main_pump"])
        return cls(client, recipe_instance, boil_kettle, mash_tun, main_pump,
                   recipe)

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
                self.state.index += 1
        Brewhouse.request_permission.register(client, self, recipe_instance)
        Brewhouse.grant_permission.register(
            client, self, recipe_instance, callback=permission_granted)

    @staticmethod
    def state_classes():
        """The state classes, in order to be executed during a brewhouse cycle.

        Provided publicly so others can inspect and export the state details
        (like order, description, etc, for the webclient to display to users).
        """
        return (
            StatePrestart,
            StatePremash,
            StateStrike,
            StatePostStrike,
            StateMash,
            StateMashoutRamp,
            StateMashoutRecirculation,
            StateSpargePrep,
            StateSparge,
            StatePreBoil,
            StateMashToBoil,
            StateBoilPreheat,
            StateBoil,
            StateCoolingPrep,
            StateCool,
            StatePumpout,
            StateDone,
        )

    def _initialize_state_machine(self):
        """Initializes state machine into fully populated state. Should be
        called by __init__.
        """
        for state in self.state_classes():
            state(self.state)
        self.state.index = 0

    def _initialize_data_streamer(self):
        """Registers variables that are @properties and need to be streamed
        periodically still.
        """
        self.data_streamer.register('boil_kettle__temperature')
        self.data_streamer.register('mash_tun__temperature')
        self.data_streamer.register('boil_kettle__power')

    def start_brewing(self):
        """Initializes a new recipe instance on the `Brewhouse`.
        Registers tracked/managed variables with the recipe instance
        assigned to the `Brewhouse`. Initializes all of the states for
        the `Brewhouse`. Schedules the periodic control tasks.
        """
        LOGGER.info('Beginning brewing instance.')

        # Schedule task 1 execution
        self.task1_rate = 1.0  # Seconds
        self.task1_lasttime = time.time()
        self.timer = None

        self.start_timers()

    def start_timers(self):
        """Schedules the control tasks for a new recipe instance on
        this `Brewhouse`.
        """
        self.timers['task00'] = ioloop.PeriodicCallback(
            self.task00, self.task1_rate*1000)

        for timer in self.timers.values():
            timer.start()

        self.data_streamer.start()

    def cancel_timers(self):
        """Stops all timers/scheduled control tasks."""
        for timer in self.timers.values():
            timer.stop()
        self.data_streamer.stop()

        self.boil_kettle.disable()
        self.mash_tun.disable()
        self.main_pump.turn_off()

    def task00(self):
        """Fast task control execution for the brewhouse system."""
        LOGGER.debug('Evaluating task 00')
        this_timer = self.timers["task00"]
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
        self.boil_kettle.regulate(this_timer)

        boil_power = self.boil_kettle.duty_cycle*self.boil_kettle.rating
        seconds_per_hours = 60.0 * 60.0
        delta_time_seconds = self.working_time - self.task1_lasttime
        delta_time_hours = delta_time_seconds / seconds_per_hours
        self.system_energy += boil_power*delta_time_hours

        # Schedule next task 1 event
        self.task1_lasttime = self.working_time

    @property
    def state_t0(self):
        """The time the current state started."""
        return self.state.state_time_change


class StatePrestart(State):
    """Everything is off. Waiting for user to initiate process after water
    is filled in the boil kettle/HLT.
    """

    NAME = 'Prestart'
    DESCRIPTION = (
        'System is offline. HLT should be filled with water. Requires'
        ' permission to proceed.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Prestart')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.request_permission = True


class StatePremash(State):
    """Boil element brings water up to strike temperature."""

    NAME = 'Premash'
    DESCRIPTION = (
        'Heating water for strike. Will request for permission to proceed when'
        ' temperature is reached. Configure hoses to pump water from HLT to'
        ' mash tun. Fill mash tun with grain.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Premash')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(
            brewhouse.recipe.strike_temperature)

        brewhouse.request_permission = (
            brewhouse.boil_kettle.temperature
            > brewhouse.recipe.strike_temperature)


class StateStrike(State):
    """The addition of hot water to the grain."""

    NAME = 'Strike'
    DESCRIPTION = (
        'Striking mash. Pumping HLT strike water into mash tun. Advance state'
        'when mash tun reaches desired volume to stop pump.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Strike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        assert len(brewhouse.recipe.mash_temperature_profile) > 0
        first_temperature = (
            brewhouse.recipe.mash_temperature_profile[0].temperature)
        brewhouse.boil_kettle.set_temperature(first_temperature)

        brewhouse.request_permission = True


class StatePostStrike(State):
    """Boil element brings water up to strike temperature."""

    NAME = 'PostStrike'
    DESCRIPTION = (
        'Pump stopped and HLT will bring water back to mash temperature. Add'
        ' enough water to cover heat exchanger coil in HLT. Requires permission'
        ' to proceed after temperature stabilizes. Configure hoses to'
        ' recirculate wort from mash tun through coil in HLT.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state PostStrike')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(
            brewhouse.mash_tun.temperature)

        assert len(brewhouse.recipe.mash_temperature_profile) > 0
        first_temperature = (
            brewhouse.recipe.mash_temperature_profile[0].temperature)
        brewhouse.boil_kettle.set_temperature(first_temperature)

        brewhouse.request_permission = (
            brewhouse.boil_kettle.temperature
            > brewhouse.boil_kettle.temperature_set_point)


class StateMash(State):
    """Pump turns on and boil element adjusts HLT temp to maintain mash
    temperature.
    """

    NAME = 'Mash'
    DESCRIPTION = (
        'Recirculating wort through HLT coil and adjusting HLT temperature to'
        ' follow mash profile and heat wort to the mash profile.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Mash')

        mash_profile = brewhouse.recipe.mash_temperature_profile

        brewhouse.timer = (
            brewhouse.state_t0
            + mash_profile.temperature_profile_length
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.enable()

        mash_temperature = mash_profile.temperature_at_time(brewhouse.state_t0)
        brewhouse.mash_tun.set_temperature(mash_temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        if brewhouse.timer <= 0.:
            self.state_machine.next_state()


class StateMashoutRamp(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water
    """

    NAME = 'MashoutRamp'
    DESCRIPTION = (
        'Heating HLT to mashout temperature while continuing to recirculate'
        ' wort.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state MashoutRamp')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.recipe.mashout_temperature)
        # Give a little extra push on boil set temp
        brewhouse.boil_kettle.set_temperature(
            brewhouse.recipe.mashout_temperature + 5.0)

        if (brewhouse.boil_kettle.temperature
                > brewhouse.recipe.mashout_temperature):
            self.state_machine.next_state()


class StateMashoutRecirculation(State):
    """Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water this continuation
    just forces an amount of time of mashout at a higher temp of wort.
    """

    NAME = 'MashoutRecirculation'
    DESCRIPTION = (
        'Recirculating wort at mashout temperature to denature enzymes and stop'
        ' the sugar conversion process.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state MashoutRecirculation')

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.recipe.mashout_time
            - brewhouse.working_time)

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.recipe.mashout_temperature)
        brewhouse.boil_kettle.set_temperature(
            brewhouse.recipe.mashout_temperature)

        brewhouse.request_permission = (brewhouse.timer <= 0.)


class StateSpargePrep(State):
    """Prep hoses for sparge process."""

    NAME = 'SpargePrep'
    DESCRIPTION = (
        'Reconfigure the hoses to pump HLT water into Mash Tun for sparging.'
        ' Configure hoses to drain out of Mash Tun into intermediate container'
        ' or directly to boil kettle.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state SpargePrep')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateSparge(State):
    """Slowly puts clean water onto grain bed as it is drained."""

    NAME = 'Sparge'
    DESCRIPTION = (
        'Pumping hot clean water from HLT into mash tun. Adjust flow with'
        ' valves to match the drain rate from the mash tun.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Sparge')

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.timer = None

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StatePreBoil(State):
    """Turns off pump to allow switching of hoses for transfer to boil as
    well as boil kettle draining.
    """

    NAME = 'PreBoil'
    DESCRIPTION = (
        'Reconfigure hoses to pump from intermediate container to the boil'
        ' kettle.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state PreBoil')

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.timer = None

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateMashToBoil(State):
    """Turns off boil element and pumps wort from mash tun to the boil kettle.
    """

    NAME = 'MashToBoil'
    DESCRIPTION = (
        'Transferring wort from intermediate container to boil kettle. Advance'
        ' state when all wort has been transferred.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state MashToBoil')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateBoilPreheat(State):
    """Heat wort up to temperature before starting to countdown timer in boil.
    """

    NAME = 'BoilPreheat'
    DESCRIPTION = (
        'Heating boil kettle to boil temperature before starting boil timer.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state BoilPreheat')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.recipe.boil_temperature)

        preheat_temperature = brewhouse.boil_kettle.temperature_set_point - 10.0
        if brewhouse.boil_kettle.temperature > preheat_temperature:
            self.state_machine.next_state()


class StateBoil(State):
    """Boiling to bring temperature to boil temp and maintain temperature for
    duration of boil.
    """

    NAME = 'Boil'
    DESCRIPTION = 'Boiling wort. Add hops at appropriate time.'

    def __call__(self, brewhouse):
        LOGGER.debug('In state Boil')

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.enable()
        brewhouse.mash_tun.disable()

        brewhouse.timer = (
            brewhouse.state_t0
            + brewhouse.recipe.boil_time
            - brewhouse.working_time)

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.recipe.boil_temperature)

        if brewhouse.timer <= 0.0:
            self.state_machine.next_state()


class StateCoolingPrep(State):
    """Idle state to switch hoses for cooling."""

    NAME = 'CoolingPrep'
    DESCRIPTION = (
        'Reconfigure hoses to circulate wort through heat exchanger and connect'
        ' cooling water. Requires permission to advance state.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Boil')

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateCool(State):
    """Cooling boil down to pitching temperature."""

    NAME = 'Cool'
    DESCRIPTION = (
        'Cooling wort down to pitching temperature by pumping wort through'
        ' heat exchanger with cold water.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Cool')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = (
            brewhouse.boil_kettle.temperature
            < brewhouse.recipe.cool_temperature)


class StatePumpout(State):
    """Pumping wort out into fermenter."""

    NAME = 'Pumpout'
    DESCRIPTION = (
        'Transferring cooled wort from boil kettle to fermenter. Advance state'
        ' when all wort has been transferred.')

    def __call__(self, brewhouse):
        LOGGER.debug('In state Pumpout')

        brewhouse.timer = None

        brewhouse.main_pump.turn_on()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.mash_tun.set_temperature(brewhouse.mash_tun.temperature)
        brewhouse.boil_kettle.set_temperature(brewhouse.boil_kettle.temperature)

        brewhouse.request_permission = True


class StateDone(State):
    """Done state. All systems off."""

    NAME = 'Done'
    DESCRIPTION = 'Brew session complete. Time to clean up!'

    def __call__(self, brewhouse):
        LOGGER.debug('In state Done')

        brewhouse.timer = None

        brewhouse.main_pump.turn_off()
        brewhouse.boil_kettle.disable()
        brewhouse.mash_tun.disable()

        brewhouse.request_permission = False
