'''
Created on Apr 3, 2016

@author: William
'''
from gpiocrust import OutputPin

class SimplePump(object):
    """A simple on/off pump."""
    def __init__(self,pin):
        self.enabled = False #default to off
        self.pin = OutputPin(pin, value=0)

    def turn_off(self):
        """Turns pump off"""
        self.enabled = False
        self.pin.value = self.enabled
    def turn_on(self):
        """Turns pump on"""
        self.enabled = True
        self.pin.value = self.enabled

    def register(self,recipe_instance):
        """Used to register sensors to recipe_instance, but this object
        has no sensors at this point.

        Args:
            recipe_instance: The id for the recipe instance to register
                this to
        """
        pass
