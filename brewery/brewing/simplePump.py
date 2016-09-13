'''
Created on Apr 3, 2016

@author: William
'''
from gpiocrust import OutputPin

class simplePump(object):
    '''
    classdocs
    '''
    def __init__(self,pin):
        '''
        Constructor
        '''
        self.enabled = False #default to off
        self.pin = OutputPin(pin, value=0)
        
    def turn_off(self):
        self.enabled = False
        self.pin.value = self.enabled
    def turn_on(self):
        self.enabled = True
        self.pin.value = self.enabled
        
    def register(self,recipe_instance):
        pass