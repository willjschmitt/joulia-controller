'''
Created on Apr 5, 2016

@author: William
'''

import logging
import time
from gpiocrust import OutputPin
from dsp import regulator, integrator
from measurement import rtdSensor
from utils import GPIO_MOCK_API_ACTIVE, OverridableVariable, StreamingVariable

LOGGER = logging.getLogger(__name__)

class SimpleVessel(object):
    """An abstract class to represent a vessel that contains liquid.

    Attributes:
        volume: Volume of liquid that is in the vessel
    """
    def __init__(self, volume,**_):
        self.volume = volume

    def set_liquid_level(self,volume):
        """Changes the current liquid level of the vessel.

        Args:
            volume: The volume now in the vessel.
        """
        self.volume = volume

class TemperatureMonitoredVessel(SimpleVessel):
    """A vessel that has a temperature sensor monitoring the temperature
    of the liquid it contains.
    """

    def __init__(self, volume, rtdParams):
        super(TemperatureMonitoredVessel,self).__init__(volume)

        self.temperature_sensor = rtdSensor(*rtdParams)

        # For simulation environment make an integrator to represent the
        # absorbtion of energy
        if GPIO_MOCK_API_ACTIVE:
            self.liquid_temperature_simulator = integrator(init=68.)

    def register(self,recipe_instance):
        """Registers this instance with the properties by submitting the
        ``recipe_instance`` to them.

        This abstract base class does not have any properties to register,
        but maintains this method to maintain the interface for class users.

        Args:
            recipe_instance: The id for the recipe instance we are
                connecting with
        """
        pass

    @property
    def temperature(self):
        """Gets the current temperature of the vessel. If GPIO is mocked,
        it will use a simulated value.
        """
        if GPIO_MOCK_API_ACTIVE:
            return self.liquid_temperature_simulator.q
        else:
            return self.temperature_sensor.temperature

    def measure_temperature(self):
        """Samples the temperature from the measurement circuit."""
        return self.temperature_sensor.measure()

class HeatedVessel(TemperatureMonitoredVessel):
    """A vessel with temperature monitoring and a heating method"""

    temperature_set_point = OverridableVariable('boilKettle__temperatureSetPoint',default=0.)
    element_status =  OverridableVariable('boilKettle__elementStatus',default=False)
    duty_cycle = StreamingVariable('boilKettle__dutyCycle')

    def __init__(self, rating, volume, rtd_params, pin, **kwargs):
        self.rating = rating # in Watts (of heating element)
        self.temperature_set_point = 0.

        self.regulator = kwargs.get('regulatorClass',regulator)(maxQ=1.,minQ=0.)

        self.duty_cycle = 0.
        self.duty_period = 1.0 #seconds

        self.pin = OutputPin(pin, value=0)

        super(HeatedVessel,self).__init__(volume,rtd_params)

        self.recalculate_gains()

    def register(self,recipe_instance):
        """Registers this instance with the properties by submitting the
        ``recipe_instance`` to them.

        Args:
            recipe_instance: The id for the recipe instance we are
                connecting with
        """
        HeatedVessel.element_status.subscribe(self,recipe_instance)
        HeatedVessel.temperature_set_point.subscribe(self,recipe_instance)
        HeatedVessel.duty_cycle.register(self,recipe_instance)
        super(HeatedVessel,self).register(recipe_instance)

    def set_temperature(self,value):
        """Sets the temperature set point for the heating element controls.
        """
        LOGGER.debug("Setting temperature %f",value)
        self.temperature_set_point = value

    def turn_off(self):
        """Disables the heating element on this vessel"""
        LOGGER.debug('Request heated vessel turn off.')
        self.element_status = self.pin.value = False
        self.regulator.disable()

    def turn_on(self):
        """Turns off the heating element on this vessel"""
        LOGGER.debug('Request heated vessel turn on.')
        self.element_status = self.pin.value = True
        self.regulator.enable()

    def set_liquid_level(self,volume):
        """Adjusts the liquid volume of the vessel, which then recalculates
        the control gains based on the new liquid volume.
        """
        self.volume = volume
        self.recalculate_gains()

    def recalculate_gains(self):
        """Calculates control gains based on the amount of liquid and
        heating rating of the heating element
        """
        self.regulator.KP = 10.*(self.volume/self.rating)
        self.regulator.KI = 100.*(self.volume/self.rating)

    def regulate(self):
        """Executes regulation action to control the temperature of the
        vessel by adjusting the duty_cycle of the heating eleement
        """
        LOGGER.debug("Temp: %f, SP: %f",self.temperature,self.temperature_set_point)
        self.duty_cycle = self.regulator.calculate(self.temperature,self.temperature_set_point)

    def measure_temperature(self):
        """Samples the temperature from the measurement circuit. If GPIO
        is mocked, we will simulate the heating action."""
        #lets here add heat to the vessel in simulation mode
        if GPIO_MOCK_API_ACTIVE:
            return self.liquid_temperature_simulator.integrate(self.temperature_ramp)
        else:
            return super(HeatedVessel,self).measure_temperature()

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
        #TODO: add better energy loss to environment
        return ((self.power - (self.temperature - 68.)*1.)
                /(self.volume*4.184*1000.)*(9./5.)*(1./3.79))


class HeatExchangedVessel(TemperatureMonitoredVessel):
    """A vessel that can be heated by by a slow heat-exchanged process,
    which includes flow as a controllable parameter.
    """

    temperature_set_point = OverridableVariable('mashTun__temperatureSetPoint')

    def __init__(self, volume, rtd_params, heat_exchanger_conductivity=1., **kwargs):
        self.volume = volume

        self.temperature_set_point = 0.
        self.source_temperature = self.temperature_set_point

        self.heat_exchanger_conductivity = heat_exchanger_conductivity
        self.regulator = kwargs.get('regulatorClass',regulator)(maxQ=15.,minQ=-15.)

        super(HeatExchangedVessel,self).__init__(volume, rtd_params)
        self.recalculate_gains()

        self.enabled = False

        self.temperature_source = kwargs.get('temperature_source',None)
        self.temperature_profile = kwargs.get('temperature_profile',None)

    def register(self,recipe_instance):
        HeatExchangedVessel.temperature_set_point.subscribe(self,recipe_instance)
        super(HeatExchangedVessel,self).register(recipe_instance)

    def turn_off(self):
        """Disables the pump on this vessel along with its controls"""
        self.enabled = False
        self.regulator.disable()

    def turn_on(self):
        """Turns on the pump for this vessel along with its controls"""
        self.enabled = True
        self.regulator.enable()

    def set_temperature(self,temp):
        """Sets the temperatures setpoint for the regulator to control
        the vessel temperature.
        """
        self.temperature_set_point = temp

    def set_temperature_profile(self,time0):
        """Sets the temperature setpoint for the controls based on the
        current time relative to the start of the temperature profile.

        Args:
            time0: The time to reference as the beginning of the profile.
        """
        if self.temperature_profile is not None:
            for temp in self.temperature_profile:
                if time.time() - time0 > temp[0]:
                    self.set_temperature(temp[1])
                    break

    @property
    def temperature_profile_length(self):
        """The total amount of time prescribed in the ``temperature_profile``
        """
        return reduce(lambda x,y: x+y[0], self.temperature_profile,0.)

    def set_liquid_level(self,volume):
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
        regulator_temperature = self.regulator.calculate(self.temperature,
                                                         self.temperature_set_point)
        self.source_temperature = self.temperature + regulator_temperature

    def recalculate_gains(self):
        """Calculates control gains based on the amount of liquid and
        heating rating of the heating element
        """
        self.regulator.KP = 2.E-1*(self.volume/self.heat_exchanger_conductivity)
        self.regulator.KI = 2.E-3*(self.volume/self.heat_exchanger_conductivity)

    def measure_temperature(self):
        """Samples the temperature from the measurement circuit. If GPIO
        is mocked, we will simulate the heating action."""
        if GPIO_MOCK_API_ACTIVE:
            return self.liquid_temperature_simulator.integrate(self.temperature_ramp)
        else:
            return super(HeatExchangedVessel,self).measure_temperature()

    @property
    def temperature_ramp(self):
        """An estimated degF/sec rate of change of liquid based on ideal
        conditions. Does not include ambient losses.
        """
        #TODO: add better energy loss to environment
        if self.temperature_source and self.enabled:
            return ((self.temperature_source.temperature - self.temperature)
                    * self.heat_exchanger_conductivity)
        else:
            return 0.
