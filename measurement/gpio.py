"""Objects for interaction with the Raspberry Pi GPIO pins.
"""


class OutputPin(object):
    """A Raspberry Pi Output pin.

    Attributes:
        gpio: The GPIO interface for interacting with the board. On the Pi, this
            is likely the RPi.GPIO library, but otherwise should be a stub.
        pin_number: The number of the pin (depends on the gpio.board_mode).
    """

    def __init__(self, gpio, pin_number):
        self.gpio = gpio
        self.pin_number = pin_number

        self.gpio.setup(self.pin_number, self.gpio.OUT)
        self._value = None
        self.value = self.gpio.LOW

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.gpio.output(self.pin_number, value)

    def set_on(self):
        self.value = self.gpio.HIGH

    def set_off(self):
        self.value = self.gpio.LOW
