'''
Created on Apr 3, 2016

@author: William
'''

from dsp.first_order_lag import FirstOrderLag

class RtdSensor(object):
    def __init__(self, analog_pin, alpha, zeroR, aRef, k, c, tau=10.0):
        self.temperature_filter = FirstOrderLag(tau)

        self.analog_in_pin = analog_pin
        self.alpha   = alpha
        self.zeroR   = zeroR
        self.analog_reference    = aRef

        self.k = k
        self.c = c

    @property
    def temperature(self):
        return self.temperature_filter.filtered

    def measure(self):
        counts = 1000 #arduino_analogRead(fd, analog_in_pin);
        if (counts < 0):
            return
        voltage_diference  = self.analog_reference*(counts/1024.)
        voltage_rtd   = voltage_diference*(15./270.) + 5.0*(10./(100.+10.))
        resistance_rtd   = (1000.*(1./5.)*voltage_rtd)/(1.-(1./5.)*voltage_rtd)
        temp = (resistance_rtd - 100.0)/self.alpha
        temp = temp*(9.0/5.0) + 32.0
        temp = temp*self.k + self.c

        self.temperature_filter.filter(temp)
