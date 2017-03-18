"""This module models and interacts with pump objects for pumping liquids.
"""


class SimplePump(object):
    """A simple on/off pump.

    Attributes:
        enabled: Boolean indicating the pump is being powered.
        pin: The gpio output pin number controlling the pump power.
    """
    def __init__(self, pin):
        self.enabled = False
        self.pin = pin

    def turn_off(self):
        """Turns pump off."""
        self.enabled = False
        self.pin.set_off()

    def turn_on(self):
        """Turns pump on."""
        self.enabled = True
        self.pin.set_on()
