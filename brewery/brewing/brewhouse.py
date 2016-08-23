'''
Created on Apr 3, 2016

@author: William
'''

import time
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient
from tornado.escape import json_decode

import urllib

from utils import dataStreamer, subscribable_variable,streaming_variable
from dsp.state_machine import StateMachine

from vessels import heatedVessel,heatExchangedVessel
from simplePump import simplePump

import logging
logger = logging.getLogger(__name__)

import settings
from settings import host,http_prefix

class Brewhouse(object):
    '''A top-level class object for operating a brewhouse. Initializes
    communication with the joulia-webserver instance, and manages
    all the equipment associated with the brewhouse system.
    '''
    grantPermission = subscribable_variable('grantPermission') #subscribes to remote var

    timer = streaming_variable('timer')
    systemEnergy = streaming_variable('systemEnergy')
    requestPermission = streaming_variable('requestPermission')

    def __init__(self,authtoken):
        '''Creates the `Brewhouse` instance and waits for a command
        from the webserver to start a new instance.
        
        Args:
            authtoken: Token string stored on joulia-webserver which
                has permission to act on behalf of this `Brewhouse` in
                order to communicate.
        '''
        logger.info('Initializing Brewery object')
        self.authtoken=authtoken
        
        self.initialize_process_state_machine()
        self.initialize_equipment()
        
        self.watch_for_start()
        
    def initialize_process_state_machine(self):
        '''Initializes the main process state machine with all of the
        serial states for conducting a recipe instance on this
        `Brewhouse`.
        '''
        states = [statePrestart,statePremash,stateStrike,
                  statePostStrike,stateMash,stateMashout,
                  stateMashout2,stateSpargePrep,stateSparge,
                  statePreBoil,stateMashToBoil,stateBoilPreheat,
                  stateBoil,stateCool,statePumpout]
        self.state = StateMachine(self,states)
        self.state.change_state('statePrestart')

    def initialize_equipment(self):
        '''Creates all the physical subelements for this `Brewhouse`
        system
        '''
        self.boilKettle = heatedVessel(rating=5000.,volume=5.,
                                       rtdParams=[0,0.385,100.0,5.0,0.94,-16.0,10.],pin=0)
        self.mashTun = heatExchangedVessel(volume=5.,
                                           rtdParams=[1,0.385,100.0,5.0,0.94,-9.0,10.],
                                           temperature_source = self.boilKettle)
        self.mainPump = simplePump(pin=2)        
        
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
                logger.info("Got command to start")
                response = json_decode(response.body)
                messages = response['messages']
                self.recipe_instance = messages['recipe_instance']
                self.start_brewing()
                self.watch_for_end()
        
        http_client = AsyncHTTPClient()
        post_data = {'brewhouse': settings.brewhouse_id}
        uri = http_prefix + ":" + host + "/live/recipeInstance/start/"
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
        uri = http_prefix + ":" + host + "/live/recipeInstance/end/"
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
        logger.info('Beginning brewing instance.')
        
        self.register(self.recipe_instance)
        
        #set state machine appropriately
        self.state.change_state('statePrestart')
        
        #permission variables
        self.requestPermission = False
        self.grantPermission   = False
        
        #reset energy integrator
        self.systemEnergy = 0.
        
        self.initialize_recipe()
        
        #schedule task 1 execution
        self.tm1Rate = 1. #seconds
        self.tm1_tz1 = time.time()
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
        self.dataStreamer = dataStreamer(self,recipe_instance)
        self.dataStreamer.register('boilKettle__temperature')
        self.dataStreamer.register('mashTun__temperature')
        self.dataStreamer.register('boilKettle__power')
        self.dataStreamer.register('systemEnergyCost')
        self.dataStreamer.register('state__id','state')
        
        #register normal time series streaming
        Brewhouse.systemEnergy.register(self,recipe_instance)
        Brewhouse.timer.register(self,recipe_instance)
        
        #register sub elements
        self.boilKettle.register(recipe_instance)
        self.mashTun.register(recipe_instance)
        self.mainPump.register(recipe_instance)
        
        #permissions handling
        def permission_granted(value): 
            if value:
                self.state.id += 1
        Brewhouse.requestPermission.register(self,recipe_instance)
        Brewhouse.grantPermission.subscribe(self,self.recipe_instance,
                                            callback=permission_granted)
        
    def initialize_recipe(self):
        '''Sets all the temperature profiles and basic recipe settings
        for the current `Brewhouse` instance.
        '''
        self.energyUnitCost = 0.15 #$/kWh
        
        #initialize everything
        self.strikeTemperature = 162.
        self.mashoutTemperature = 170.
        self.mashoutTime = 10.*60. # in seconds
        self.boilTemperature = 217.
        self.coolTemperature = 70.
        self.mashTemperatureProfile = [
            [45.*60., 152.0], #start at 152
            [15.*60.,155.0], #at 45min step up to 155
        ]
        self.mashTun.temperature_profile=self.mashTemperatureProfile
           
    def end_brewing(self):
        '''Terminates a currently running recipe instance on this
        `Brewhouse`. Cancels the task schedules and returns to waiting
        for a new recipe instance to be requested
        '''
        logger.info('Ending brewing instance.')
        self.end_timer()
        
        self.watch_for_start()
        return
    
    def start_timer(self):
        '''Schedules the control tasks for a new recipe instance on
        this `Brewhouse`.
        '''
        self.timers = {}
        self.timers['task00'] = ioloop.PeriodicCallback(self.task00,self.tm1Rate*1000)
        self.timers['task00'].start()
        
    def end_timer(self):
        '''Stops all timers/scheduled control tasks.'''
        for timer in self.timers.itervalues():
            timer.stop()
         
    def task00(self):
        logger.debug('Evaluating task 00')
        self.wtime = time.time()
    
        # Evaluate state of controls (mash, pump, boil, etc)
        self.state.evaluate()
    
        # Check Temperatures
        self.boilKettle.measureTemperature()
        self.mashTun.measureTemperature()
    
        # Controls Calculations for Mash Tun Element
        self.mashTun.regulate()
        #TODO: probably need to figure out better option rather than just checking if its regulator is enabled
        if self.mashTun.regulator.enabled:
            self.boilKettle.setTemperature(self.mashTun.sourceTemperature)
    
        # Controls Calculations for Boil Kettle Element
        self.boilKettle.regulate()

        boil_power = self.boilKettle.dutyCycle*self.boilKettle.rating
        delta_time_hours = (self.wtime-self.tm1_tz1)/(60.*60.)
        self.systemEnergy += boil_power*delta_time_hours
        self.systemEnergyCost = (self.systemEnergy/1000.
                                 * self.energyUnitCost)
        
#         self.dataStreamer.postData()
        
        #schedule next task 1 event
        self.tm1_tz1 = self.wtime
        
    
def statePrestart(breweryInstance):
    '''
    __STATE_PRESTART - state where everything is off. waiting for user to
    okay start of process after water is filled in the boil kettle/HLT
    '''
    logger.debug('In statePrestart')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()

    breweryInstance.requestPermission = True
        
def statePremash(breweryInstance): 
    '''
    __STATE_PREMASH - state where the boil element brings water up to
    strike temperature
    '''
    logger.debug('In statePremash')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.strikeTemperature)

    if breweryInstance.boilKettle.temperature > breweryInstance.strikeTemperature:
        breweryInstance.requestPermission = True

def stateStrike(breweryInstance):
    logger.debug('In stateStrike')
    
    breweryInstance.timer = None

    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.mashTun.temperature_profile[0][1])
    

    breweryInstance.requestPermission = True

def statePostStrike(breweryInstance):
    '''
    C_STATE_PREMASH - state where the boil element brings water up to
    strike temperature
    '''
    logger.debug('In statePostStrike')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.mashTun.temperature_profile[0][1])

    if breweryInstance.boilKettle.temperature > breweryInstance.mashTun.temperatureSetPoint:
        breweryInstance.requestPermission = True

def stateMash(breweryInstance):
    '''
    C_STATE_MASH - state where pump turns on and boil element adjusts HLT temp
    to maintain mash temperature
    '''
    logger.debug('In stateMash')
    
    breweryInstance.timer = (breweryInstance.state_t0 + breweryInstance.mashTun.temperature_profile_length) - breweryInstance.wtime

    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOn()

    breweryInstance.mashTun.setTemperatureProfile(breweryInstance.state_t0)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)
    breweryInstance.timeT0 = time.time()

    if breweryInstance.timer <= 0.:
        breweryInstance.state.change_state('stateMashout')

def stateMashout(breweryInstance):
    '''
    C_STATE_MASHOUT - steps up boil temperature to 175degF and continues
    to circulate wort to stop enzymatic processes and to prep sparge water
    '''
    logger.debug('In stateMashout')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOn()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashoutTemperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.mashoutTemperature+5.) #give a little extra push on boil set temp 
    
    if breweryInstance.boilKettle.temperature > breweryInstance.mashoutTemperature:
        breweryInstance.state.change_state('stateMashout2')

def stateMashout2(breweryInstance):
    '''
    C_STATE_MASHOUT2 - steps up boil temperature to 175degF and continues
    to circulate wort to stop enzymatic processes and to prep sparge water
    this continuation just forces an amount of time of mashout at a higher
    temp of wort
    '''
    logger.debug('In stateMashout2')
    
    breweryInstance.timer = (breweryInstance.state_t0 + breweryInstance.mashoutTime) - breweryInstance.wtime
    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashoutTemperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)
    if breweryInstance.timer <= 0.:
        breweryInstance.requestPermission = True

def stateSpargePrep(breweryInstance):
    '''
    C_STATE_SPARGEPREP - prep hoses for sparge process
    '''
    logger.debug('In stateSpargePrep')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)

    breweryInstance.requestPermission = True

def stateSparge(breweryInstance):
    '''
    C_STATE_SPARGE - slowly puts clean water onto grain bed as it is 
    drained
    '''
    logger.debug('In stateSparge')
    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()

    breweryInstance.timer = None

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)

    breweryInstance.requestPermission = True

def statePreBoil(breweryInstance):
    '''
    C_STATE_PREBOIL - turns of pump to allow switching of hoses for
    transfer to boil as well as boil kettle draining
    '''
    logger.debug('In statePreBoil')
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()
    
    breweryInstance.timer = None
    
    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)
    
    breweryInstance.requestPermission = True

def stateMashToBoil(breweryInstance):
    '''
    C_STATE_MASHTOBOIL - turns off boil element and pumps wort from
    mash tun to the boil kettle
    '''
    logger.debug('In stateMashToBoil')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()
    
    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)
    
    breweryInstance.requestPermission = True

def stateBoilPreheat(breweryInstance):
    '''
    C_STATE_BOILPREHEAT - heat wort up to temperature before starting to
    countdown timer in boil.
    '''
    logger.debug('In stateBoilPreheat')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilTemperature)
    
    if breweryInstance.boilKettle.temperature >  breweryInstance.boilKettle.temperatureSetPoint - 10.0:
        breweryInstance.state.change_state('stateBoil')

def stateBoil(breweryInstance):
    '''
        C_STATE_BOIL - state of boiling to bring temperature to boil temp
        and maintain temperature for duration of boil
    '''
    logger.debug('In stateBoil')
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()
    
    breweryInstance.timer = (breweryInstance.state_t0 + breweryInstance.BOILTIME) - breweryInstance.wtime

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilTemperature)
    breweryInstance.timeT0 = time.time()

    if breweryInstance.timer <= 0.:
        breweryInstance.requestPermission = True

def stateCool(breweryInstance):
    '''
    C_STATE_COOL - state of cooling boil down to pitching temperature
    '''
    logger.debug('In stateCool')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOff()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)
    
    if breweryInstance.boilKettle.temperature < breweryInstance.coolTemperature:
        breweryInstance.requestPermission = True

def statePumpout(breweryInstance):
    '''
    C_STATE_PUMPOUT - state of pumping wort out into fermenter
    '''
    logger.debug('In statePumpout')
    
    breweryInstance.timer = None
    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOff()
    breweryInstance.mashTun.turnOff()

    breweryInstance.mashTun.setTemperature(breweryInstance.mashTun.temperature)
    breweryInstance.boilKettle.setTemperature(breweryInstance.boilKettle.temperature)

    breweryInstance.requestPermission = True