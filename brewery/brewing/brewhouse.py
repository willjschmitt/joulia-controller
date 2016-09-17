'''
Created on Apr 3, 2016

@author: William
'''

import logging
import time
import urllib

from tornado import ioloop
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient

from brewery.brewing.simple_pump import SimplePump
from brewery.brewing.vessels import HeatedVessel, HeatExchangedVessel
from dsp.state_machine import StateMachine
from settings import HOST, HTTP_PREFIX
import settings
from utils import DataStreamer, SubscribableVariable, StreamingVariable

LOGGER = logging.getLogger(__name__)

class Brewhouse(object):
    '''A top-level class object for operating a brewhouse. Initializes
    communication with the joulia-webserver instance, and manages
    all the equipment associated with the brewhouse system.
    '''
    grant_permission = SubscribableVariable('grant_permission') #subscribes to remote var

    timer = StreamingVariable('timer')
    system_energy = StreamingVariable('system_energy')
    request_permission = StreamingVariable('request_permission')

    def __init__(self,AUTHTOKEN):
        '''Creates the `Brewhouse` instance and waits for a command
        from the webserver to start a new instance.

        Args:
            AUTHTOKEN: Token string stored on joulia-webserver which
                has permission to act on behalf of this `Brewhouse` in
                order to communicate.
        '''
        LOGGER.info('Initializing Brewery object')
        self.authtoken=AUTHTOKEN

        self.recipe_instance = None
        self.data_streamer = None

        self.energy_unit_cost = 0.15 #$/kWh

        self.strike_temperature = 0.0
        self.mashout_temperature = 0.0
        self.mashout_time = 0.0 # in seconds
        self.boil_temperature = 0.0
        self.boil_time = 0.0 # seconds
        self.cool_temperature = 0.0
        self.mash_temperature_profile = []

        self.working_time = None
        self.timers = {}
        self.task1_rate = 1.0 #seconds
        self.task1_lasttime = time.time()

        self.initialize_process_state_machine()
        self.initialize_equipment()

        self.watch_for_start()

    def initialize_process_state_machine(self):
        '''Initializes the main process state machine with all of the
        serial states for conducting a recipe instance on this
        `Brewhouse`.
        '''
        states = [state_prestart,state_premash,state_strike,
                  state_post_strike,state_mash,state_mashout_ramp,
                  state_mashout_recirculation,state_sparge_prep,state_sparge,
                  state_pre_boil,state_mash_to_boil,state_boil_preheat,
                  state_boil,state_cool,state_pumpout]
        self.state = StateMachine(self,states)
        self.state.change_state('state_prestart')

    def initialize_equipment(self):
        '''Creates all the physical subelements for this `Brewhouse`
        system
        '''
        self.boil_kettle = HeatedVessel(rating=5000.,volume=5.,
                                        rtd_params=[0,0.385,100.0,5.0,0.94,-16.0,10.],
                                        pin=0)
        self.mash_tun = HeatExchangedVessel(volume=5.,
                                           rtd_params=[1,0.385,100.0,5.0,0.94,-9.0,10.],
                                           temperature_source = self.boil_kettle)
        self.main_pump = SimplePump(pin=2)

    def watch_for_start(self):
        '''Makes a long-polling request to joulia-webserver to check
        if the server received a request to start a brewing session.

        Once the request completes, the internal method
        handle_start_request is executed.
        '''
        def handle_start_request(response):
            '''Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the startup
            logic for this Brewhouse
            '''
            if response.error:
                logging.error(response)
                self.watch_for_start()
            else:
                LOGGER.info("Got command to start")
                response = json_decode(response.body)
                messages = response['messages']
                self.recipe_instance = messages['recipe_instance']
                self.start_brewing()
                self.watch_for_end()

        http_client = AsyncHTTPClient()
        post_data = {'brewhouse': settings.brewhouse_id}
        uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/start/"
        headers = {'Authorization':'Token ' + self.authtoken}
        http_client.fetch(uri, handle_start_request,
                          headers=headers,
                          method="POST",
                          body=urllib.urlencode(post_data))

    def watch_for_end(self):
        '''Makes a long-polling request to joulia-webserver to check
        if the server received a request to end the brewing session.

        Once the request completes, the internal method
        handle_end_request is executed.
        '''
        def handle_end_request(response):
            '''Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the termination
            logic for this Brewhouse
            '''
            if response.error:
                self.watch_for_end()
            else:
                self.end_brewing()

        http_client = AsyncHTTPClient()
        post_data = {'brewhouse': settings.brewhouse_id}
        uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/end/"
        headers = {'Authorization':'Token ' + self.authtoken}
        http_client.fetch(uri, handle_end_request,
                          headers=headers,
                          method="POST",
                          body=urllib.urlencode(post_data))

    def start_brewing(self):
        '''Initializes a new recipe instance on the `Brewhouse`.
        Registers tracked/managed variables with the recipe instance
        assigned to the `Brewhouse`. Initializes all of the states for
        the `Brewhouse`. Schedules the periodic control tasks.
        '''
        LOGGER.info('Beginning brewing instance.')

        self.register(self.recipe_instance)

        #set state machine appropriately
        self.state.change_state('state_prestart')

        #permission variables
        self.request_permission = False
        self.grant_permission   = False

        #reset energy integrator
        self.system_energy = 0.0

        self.initialize_recipe()

        #schedule task 1 execution
        self.task1_rate = 1.0 #seconds
        self.task1_lasttime = time.time()
        self.timer = None
        self.task00()

        self.start_timer()

    def register(self,recipe_instance):
        '''Registers the tracked/managed variables with the recipe
        instance. This allows for the variables to be changed as native
        attributes of the `Brewhouse` and child elements, while
        streaming changes as they happen locally, or receiving changes
        as they happen remotely'''

        self.state.register(recipe_instance)

        #variables that are @properties and need to be streamed periodically still
        self.data_streamer = DataStreamer(self,recipe_instance)
        self.data_streamer.register('boilKettle__temperature')
        self.data_streamer.register('mashTun__temperature')
        self.data_streamer.register('boilKettle__power')
        self.data_streamer.register('system_energy_cost')
        self.data_streamer.register('state__id','state')

        #register normal time series streaming
        Brewhouse.system_energy.register(self,recipe_instance)
        Brewhouse.timer.register(self,recipe_instance)

        #register sub elements
        self.boil_kettle.register(recipe_instance)
        self.mash_tun.register(recipe_instance)
        self.main_pump.register(recipe_instance)

        def permission_granted(value):
            """If permission is granted, increments the state"""
            if value:
                self.state.id += 1
        Brewhouse.request_permission.register(self,recipe_instance)
        Brewhouse.grant_permission.subscribe(self,self.recipe_instance,
                                            callback=permission_granted)

    def initialize_recipe(self):
        '''Sets all the temperature profiles and basic recipe settings
        for the current `Brewhouse` instance.
        '''
        #initialize everything
        self.strike_temperature = 162.
        self.mashout_temperature = 170.
        self.mashout_time = 10.*60. # in seconds
        self.boil_temperature = 217.
        self.boil_time = 60.*60. # seconds
        self.cool_temperature = 70.
        self.mash_temperature_profile = [
            [45.*60., 152.0], #start at 152
            [15.*60.,155.0], #at 45min step up to 155
        ]
        self.mash_tun.temperature_profile=self.mash_temperature_profile

    def end_brewing(self):
        '''Terminates a currently running recipe instance on this
        `Brewhouse`. Cancels the task schedules and returns to waiting
        for a new recipe instance to be requested
        '''
        LOGGER.info('Ending brewing instance.')
        self.end_timer()

        self.watch_for_start()
        return

    def start_timer(self):
        '''Schedules the control tasks for a new recipe instance on
        this `Brewhouse`.
        '''
        self.timers['task00'] = ioloop.PeriodicCallback(self.task00,self.task1_rate*1000)
        self.timers['task00'].start()

    def end_timer(self):
        '''Stops all timers/scheduled control tasks.'''
        for timer in self.timers.itervalues():
            timer.stop()

    def task00(self):
        """Fast task control execution for the brewhouse system"""
        LOGGER.debug('Evaluating task 00')
        self.working_time = time.time()

        # Evaluate state of controls (mash, pump, boil, etc)
        self.state.evaluate()

        # Check Temperatures
        self.boil_kettle.measure_temperature()
        self.mash_tun.measure_temperature()

        # Controls Calculations for Mash Tun Element
        self.mash_tun.regulate()
        #TODO: (Will) probably need to figure out better option rather than
        # just checking if its Regulator is enabled
        if self.mash_tun.Regulator.enabled:
            self.boil_kettle.set_temperature(self.mash_tun.source_temperature)

        # Controls Calculations for Boil Kettle Element
        self.boil_kettle.regulate()

        boil_power = self.boil_kettle.duty_cycle*self.boil_kettle.rating
        delta_time_hours = (self.working_time-self.task1_lasttime)/(60.*60.)
        self.system_energy += boil_power*delta_time_hours

        #schedule next task 1 event
        self.task1_lasttime = self.working_time

    @property
    def system_energy_cost(self):
        """The total energy cost from this recipe instance."""
        return (self.system_energy/1000.) * self.energy_unit_cost


def state_prestart(brewery_instance):
    '''Everything is off. Waiting for user to initiate process after water
    is filled in the boil kettle/HLT.
    '''
    LOGGER.debug('In state_prestart')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.request_permission = True

def state_premash(brewery_instance):
    '''Boil element brings water up to strike temperature'''
    LOGGER.debug('In state_premash')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.strike_temperature)

    if brewery_instance.boil_kettle.temperature > brewery_instance.strike_temperature:
        brewery_instance.request_permission = True

def state_strike(brewery_instance):
    """The addition of hot water to the grain"""
    LOGGER.debug('In state_strike')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()


    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)

    first_temperature = brewery_instance.mash_tun.temperature_profile[0][1]
    brewery_instance.boil_kettle.set_temperature(first_temperature)

    brewery_instance.request_permission = True

def state_post_strike(brewery_instance):
    '''Boil element brings water up to strike temperature'''
    LOGGER.debug('In state_post_strike')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)

    first_temperature = brewery_instance.mash_tun.temperature_profile[0][1]
    brewery_instance.boil_kettle.set_temperature(first_temperature)

    if brewery_instance.boil_kettle.temperature > brewery_instance.mash_tun.temperature_set_point:
        brewery_instance.request_permission = True

def state_mash(brewery_instance):
    '''Pump turns on and boil element adjusts HLT temp to maintain mash
    temperature
    '''
    LOGGER.debug('In state_mash')

    brewery_instance.timer = (brewery_instance.state_t0
                              + brewery_instance.mash_tun.temperature_profile_length
                              - brewery_instance.working_time)

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_on()

    brewery_instance.mash_tun.set_temperature_profile(brewery_instance.state_t0)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)
    brewery_instance.timeT0 = time.time()

    if brewery_instance.timer <= 0.:
        brewery_instance.state.change_state('state_mashout_ramp')

def state_mashout_ramp(brewery_instance):
    '''Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water
    '''
    LOGGER.debug('In state_mashout_ramp')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_on()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mashout_temperature)
    # Give a little extra push on boil set temp
    brewery_instance.boil_kettle.set_temperature(brewery_instance.mashout_temperature+5.)

    if brewery_instance.boil_kettle.temperature > brewery_instance.mashout_temperature:
        brewery_instance.state.change_state('state_mashout_recirculation')

def state_mashout_recirculation(brewery_instance):
    '''Steps up boil temperature to 175degF and continues to circulate wort
    to stop enzymatic processes and to prep sparge water this continuation
    just forces an amount of time of mashout at a higher temp of wort
    '''
    LOGGER.debug('In state_mashout_recirculation')

    brewery_instance.timer = (brewery_instance.state_t0
                              + brewery_instance.mashout_time
                              - brewery_instance.working_time)

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mashout_temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)
    if brewery_instance.timer <= 0.:
        brewery_instance.request_permission = True

def state_sparge_prep(brewery_instance):
    '''Prep hoses for sparge process'''
    LOGGER.debug('In state_sparge_prep')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    brewery_instance.request_permission = True

def state_sparge(brewery_instance):
    '''Slowly puts clean water onto grain bed as it is drained'''
    LOGGER.debug('In state_sparge')

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.timer = None

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    brewery_instance.request_permission = True

def state_pre_boil(brewery_instance):
    '''Turns off pump to allow switching of hoses for transfer to boil as
    well as boil kettle draining
    '''
    LOGGER.debug('In state_pre_boil')

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.timer = None

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    brewery_instance.request_permission = True

def state_mash_to_boil(brewery_instance):
    '''Turns off boil element and pumps wort from mash tun to the boil kettle
    '''
    LOGGER.debug('In state_mash_to_boil')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    brewery_instance.request_permission = True

def state_boil_preheat(brewery_instance):
    '''Heat wort up to temperature before starting to countdown timer in boil.
    '''
    LOGGER.debug('In state_boil_preheat')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_temperature)

    preheat_temperature = brewery_instance.boil_kettle.temperature_set_point - 10.0
    if brewery_instance.boil_kettle.temperature >  preheat_temperature:
        brewery_instance.state.change_state('state_boil')

def state_boil(brewery_instance):
    '''Boiling to bring temperature to boil temp and maintain temperature
    for duration of boil
    '''
    LOGGER.debug('In state_boil')

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_on()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.timer = (brewery_instance.state_t0
                              + brewery_instance.boil_time
                              - brewery_instance.working_time)

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_temperature)
    brewery_instance.timeT0 = time.time()

    if brewery_instance.timer <= 0.:
        brewery_instance.request_permission = True

def state_cool(brewery_instance):
    '''Cooling boil down to pitching temperature'''
    LOGGER.debug('In state_cool')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_off()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    if brewery_instance.boil_kettle.temperature < brewery_instance.cool_temperature:
        brewery_instance.request_permission = True

def state_pumpout(brewery_instance):
    '''Pumping wort out into fermenter'''
    LOGGER.debug('In state_pumpout')

    brewery_instance.timer = None

    brewery_instance.main_pump.turn_on()
    brewery_instance.boil_kettle.turn_off()
    brewery_instance.mash_tun.turn_off()

    brewery_instance.mash_tun.set_temperature(brewery_instance.mash_tun.temperature)
    brewery_instance.boil_kettle.set_temperature(brewery_instance.boil_kettle.temperature)

    brewery_instance.request_permission = True
