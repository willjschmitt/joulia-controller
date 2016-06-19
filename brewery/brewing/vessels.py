'''
Created on Apr 5, 2016

@author: William
'''

import logging
logger = logging.getLogger(__name__)

import time

from gpiocrust import OutputPin
from utils import gpio_mock_api_active, overridable_variable

from measurement import rtdSensor

from dsp import regulator, integrator

from settings import recipe_instance

class simpleVessel(object):
    '''
    classdocs
    '''
    def __init__(self, volume,**kwargs):
        '''
        Constructor
        '''
        self.volume = volume
    
    def setLiquidLevel(self,volume):
        self.volume = volume

class temperatureMonitoredVessel(simpleVessel):
    '''
    classdocs
    '''
    def __init__(self, volume, rtdParams):
        '''
        Constructor
        '''
        super(temperatureMonitoredVessel,self).__init__(volume)
        
        self.temperatureSensor = rtdSensor(*rtdParams)
        
        #for simulation environment make an integrator to represent the absorbtion of energy     
        if gpio_mock_api_active:
            self.liquid_temperature_simulator = integrator(init=68.)
            
    @property
    def temperature(self):
        if gpio_mock_api_active:
            return self.liquid_temperature_simulator.q
        else:
            return self.temperatureSensor.temperature
        
    def measureTemperature(self):
        return self.temperatureSensor.measure()
    
    
class heatedVessel(temperatureMonitoredVessel):
    '''
    classdocs
    '''

    elementStatus =  overridable_variable('boilKettle__elementStatus') #subscribes to remote var

    def __init__(self, rating, volume, rtdParams, pin, **kwargs):
        '''
        Constructor
        '''
        self.rating = rating # in Watts (of heating element)
        self.elementStatus = False # element defaults to off
        def printval(val):
            print val, self.elementStatus, heatedVessel.elementStatus.overridden[self]
        heatedVessel.elementStatus.subscribe(self,recipe_instance,callback=printval)
        
        self.temperatureSetPoint = 0.
        
        
                
        self.regulator = kwargs.get('regulatorClass',regulator)(maxQ=1.,minQ=0.)
        
        self.dutyCycle = 0.
        self.dutyPeriod = 1. #seconds
        
        self.pin = OutputPin(pin, value=0)
        
        super(heatedVessel,self).__init__(volume,rtdParams)
        
        self.recalculateGains()
        
    def setTemperature(self,value): 
        logger.debug("Setting temperature {}".format(value))
        self.temperatureSetPoint = value
        
    def turnOff(self):
        logger.debug('Request heated vessel turn off.')
        self.elementStatus = self.pin.value = False
        self.regulator.disable()
        logger.debug('Element is on: {}'.format(self.elementStatus))
    def turnOn(self): 
        logger.debug('Request heated vessel turn on.') 
        self.elementStatus = self.pin.value = True
        self.regulator.enable()
        logger.debug('Element is on: {}'.format(self.elementStatus))
    
    def setLiquidLevel(self,volume):
        self.volume = volume
        self.recalculateGains()
    
    def recalculateGains(self):
        self.regulator.KP = 10.*(self.volume/self.rating)
        self.regulator.KI = 100.*(self.volume/self.rating)
        
    def regulate(self):
        logger.debug("Temp: {}, SP: {}".format(self.temperature,self.temperatureSetPoint))
        self.dutyCycle = self.regulator.calculate(self.temperature,self.temperatureSetPoint)
    
    
    def measureTemperature(self):
        #lets here add heat to the vessel in simulation mode
        if gpio_mock_api_active: 
            return self.liquid_temperature_simulator.integrate(self.temperature_ramp)
        else:
            return super(heatedVessel,self).measureTemperature()
        
    @property
    def power(self): return self.dutyCycle * self.rating * self.elementStatus
    
    @property #returns degF/sec rate of change of liquid
    def temperature_ramp(self):
        #TODO: add better energy loss to environment
        return (self.power - (self.temperature - 68.)*1.)/(self.volume*4.184*1000.)*(9./5.)*(1./3.79)

        
class heatExchangedVessel(temperatureMonitoredVessel):
    '''
    classdocs
    '''

    def __init__(self, volume, rtdParams,heatExchangerConductivity=1., **kwargs):
        '''
        Constructor
        '''
        self.volume = volume
        
        self.temperatureSetPoint = 0.
        
        self.heatExchangerConductivity = heatExchangerConductivity
        self.regulator = kwargs.get('regulatorClass',regulator)(maxQ=15.,minQ=-15.)
        
        super(heatExchangedVessel,self).__init__(volume, rtdParams)
        self.recalculateGains()
        
        self.enabled = False
 
        self.temperature_source = kwargs.get('temperature_source',None)
        self.temperature_profile = kwargs.get('temperature_profile',None)
        
    def turnOff(self):
        self.enabled = False
        self.regulator.disable()
    def turnOn(self):
        self.enabled = True
        self.regulator.enable()
    
    def setTemperature(self,temp):
        self.temperatureSetPoint = temp

    def setTemperatureProfile(self,time0):
        if self.temperature_profile is not None:
            for temp in self.temperature_profile:
                if time.time() - time0 > temp[0]:
                    self.setTemperature(temp[1])
                    break
                
    @property
    def temperature_profile_length(self):
        return reduce(lambda x,y: x+y[0], self.temperature_profile,0.)
        
    def setLiquidLevel(self,volume):
        self.volume = volume
        self.recalculateGains()
        
    def regulate(self):
        self.sourceTemperature = self.temperature + self.regulator.calculate(self.temperature,self.temperatureSetPoint)
        
    def recalculateGains(self):
        self.regulator.KP = 2.E-1*(self.volume/self.heatExchangerConductivity)
        self.regulator.KI = 2.E-3*(self.volume/self.heatExchangerConductivity)
    
    def measureTemperature(self):
        #lets here add heat to the vessel in simulation mode
        if gpio_mock_api_active: 
            return self.liquid_temperature_simulator.integrate(self.temperature_ramp)
        else:
            return super(heatedVessel,self).measureTemperature()
        
    @property #returns degF/sec rate of change of liquid
    def temperature_ramp(self):
        #TODO: add better energy loss to environment
        if self.temperature_source and self.enabled:
            return (self.temperature_source.temperature - self.temperature) * self.heatExchangerConductivity
        else:
            return 0.