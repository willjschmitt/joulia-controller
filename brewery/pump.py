"""This module models and interacts with pump objects for pumping liquids.
"""

import logging

from measurement.gpio import OutputPin
from variables import OverridableVariable
from variables import SubscribableVariable

LOGGER = logging.getLogger(__name__)


class SimplePump(object):
    """A simple on/off pump.

    Attributes:
        pump_status: Boolean indicating the pump is being powered.
        pin: The gpio output pin number controlling the pump power.
    """

    emergency_stop = SubscribableVariable('emergency_stop', default=False)
    pump_status = OverridableVariable('main_pump__pump_status', default=False)

    def __init__(self, client, recipe_instance, pin):
        self._register(client, recipe_instance)
        self.enabled = False
        self.pin = pin

    @classmethod
    def from_json(cls, client, gpio, recipe_instance, configuration):
        """Factory for creating a SimplePump from JSON configuration."""
        pin = OutputPin(gpio, configuration["pin"])
        return cls(client, recipe_instance, pin)

    def _register(self, client, recipe_instance):
        """Registers this instance with the properties by submitting the
        ``recipe_instance`` to them.

        Args:
            client: The websocket client used for communicated with the server.
            recipe_instance: The id for the recipe instance we are
                connecting with
        """
        SimplePump.emergency_stop.register(client, self, recipe_instance)
        SimplePump.pump_status.register(client, self, recipe_instance)

    def turn_off(self):
        """Turns pump off."""
        self.pump_status = False
        self.pin.set_off()

    def turn_on(self):
        """Turns pump on."""
        if self.emergency_stop:
            LOGGER.info('Emergency stop engaged. Redirecting to turn_off call.')
            self.turn_off()
            return
        self.pump_status = True
        self.pin.set_on()
