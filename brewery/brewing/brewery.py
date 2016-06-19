'''
Created on Apr 3, 2016

@author: William
'''

import sched,time
from tornado import ioloop

from utils import dataStreamer, subscribable_variable,streaming_variable
from dsp import stateMachine

from vessels import heatedVessel,heatExchangedVessel
from simplePump import simplePump

import logging
logger = logging.getLogger(__name__)

from settings import recipe_instance

class brewery(object):
    '''
    classdocs
    '''
    grantPermission = subscribable_variable('grantPermission') #subscribes to remote var

    timer = streaming_variable('timer')
    systemEnergy = streaming_variable('systemEnergy')
    requestPermission = streaming_variable('requestPermission')

    def __init__(self):
        '''
        Constructor
        '''
        logger.info('Initializing Brewery object')
        self.scheduler = sched.scheduler(time.time,time.sleep)
        
        self.recipeInstance = 1
        
        #variables that are @properties and need to be streamed periodically still
        self.dataStreamer = dataStreamer(self,recipe_instance)
        self.dataStreamer.register('boilKettle__temperature')
        self.dataStreamer.register('boilKettle__elementStatus')
        self.dataStreamer.register('mashTun__temperature')
        self.dataStreamer.register('boilKettle__power')
        self.dataStreamer.register('systemEnergyCost')
        self.dataStreamer.register('state__id','state')
        
        #state machine initialization
        self.state = stateMachine(self)
        self.state.addState(statePrestart)
        self.state.addState(statePremash)
        self.state.addState(stateStrike)
        self.state.addState(statePostStrike)
        self.state.addState(stateMash)
        self.state.addState(stateMashout)
        self.state.addState(stateMashout2)
        self.state.addState(stateSpargePrep)
        self.state.addState(stateSparge)
        self.state.addState(statePreBoil)
        self.state.addState(stateMashToBoil)
        self.state.addState(stateBoilPreheat)
        self.state.addState(stateBoil)
        self.state.addState(stateCool)
        self.state.addState(statePumpout)
        self.state.changeState('statePrestart')
    
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
        
        brewery.systemEnergy.register(self,recipe_instance)
        self.systemEnergy = 0.
        self.energyUnitCost = 0.15 #$/kWh
        
        
        self.boilKettle = heatedVessel(rating=5000.,volume=5.,rtdParams=[0,0.385,100.0,5.0,0.94,-16.0,10.],pin=0)
        self.mashTun = heatExchangedVessel(volume=5.,rtdParams=[1,0.385,100.0,5.0,0.94,-9.0,10.],temperature_source = self.boilKettle,temperature_profile=self.mashTemperatureProfile)
        self.mainPump = simplePump(pin=2)        
    
        #permission variables
        brewery.requestPermission.register(self,recipe_instance)
        self.requestPermission = False
        self.grantPermission   = False
        def permissionGranted(value): 
            if value:
                self.state.id += 1
        brewery.grantPermission.subscribe(self,recipe_instance,callback=permissionGranted)
        
        #schedule task 1 execution
        self.tm1Rate = 1. #seconds
        self.tm1_tz1 = time.time()
        brewery.timer.register(self,recipe_instance)
        self.timer = None
        self.task00()
        
        a = ioloop.PeriodicCallback(self.task00,self.tm1Rate*1000)
        a.start()
        
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

        self.systemEnergy += (self.boilKettle.dutyCycle*self.boilKettle.rating)*((self.wtime-self.tm1_tz1)/(60.*60.))
        self.systemEnergyCost= self.systemEnergy/1000. * self.energyUnitCost
        
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

    breweryInstance.boilKettle.setTemperature(breweryInstance.strikeTemperature)

    if breweryInstance.boilKettle.temperature > breweryInstance.strikeTemperature:
        breweryInstance.requestPermission = True

def stateStrike(breweryInstance):
    logger.debug('In stateStrike')
    
    breweryInstance.timer = None

    
    breweryInstance.mainPump.turnOn()
    breweryInstance.boilKettle.turnOn()
    breweryInstance.mashTun.turnOff()

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
    breweryInstance.timeT0 = time.time()

    if breweryInstance.timer <= 0.:
        breweryInstance.state.changeState('stateMashout')

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
        breweryInstance.state.changeState('stateMashout2')

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

    breweryInstance.boilKettle.setTemperature(breweryInstance.boilTemperature)
    
    if breweryInstance.boilKettle.temperature >  breweryInstance.boilKettle.temperatureSetPoint - 10.0:
        breweryInstance.state.changeState('stateBoil')

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

    breweryInstance.requestPermission = True