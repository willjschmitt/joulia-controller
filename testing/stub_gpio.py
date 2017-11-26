"""Stub interface for the GPIO on a Raspberry Pi board. Provides mocks for the
RPi.GPIO library."""

from enum import Enum


class BoardMode(Enum):
    """Mocks the values of BOARD and BCM in the RPi.GPIO library."""
    BOARD = 0
    BCM = 1


class PinState(Enum):
    """Mocks the values of LOW and HIGH in the RPi.GPIO library."""
    LOW = False
    HIGH = True


class PinMode(Enum):
    """Mocks the values of IN and OUT in the RPi.GPIO library."""
    IN = 0  # pylint: disable=invalid-name
    OUT = 1


class StubGPIO(object):
    """A mock interface to the Raspberry Pi GPIO, mocking the RPi.GPIO library.

    Enforces the use of GPIO constants for setting states like GPIO.LOW, etc...
    """
    LOW = PinState.LOW
    HIGH = PinState.HIGH

    IN = PinMode.IN  # pylint: disable=invalid-name
    OUT = PinMode.OUT

    BOARD = BoardMode.BOARD
    BCM = BoardMode.BCM

    def __init__(self):
        self.pin_modes = {}
        self.values = {}
        self.board_mode = None

    def setmode(self, board_mode):
        """Mocks setmode in the RPi.GPIO library."""
        assert board_mode in BoardMode
        self.board_mode = board_mode

    def setup(self, pin, pin_mode):
        """Mocks setup in the RPi.GPIO library."""
        assert pin_mode in PinMode
        self.pin_modes[pin] = pin_mode

    def output(self, pin, value):
        """Mocks output in the RPi.GPIO library."""
        assert value in PinState
        if pin not in self.pin_modes:
            raise RuntimeError("Pin mode must be set before setting value.")

        if self.pin_modes[pin] is not self.OUT:
            raise RuntimeError("Pin mode must be StubGPIO.OUT to set value.")

        self.values[pin] = value

    def input(self, pin):
        """Mocks input in the RPi.GPIO library."""
        if pin not in self.pin_modes:
            raise RuntimeError("Pin mode must be set before setting value.")

        if self.pin_modes[pin] is not self.IN:
            raise RuntimeError("Pin mode must be StubGPIO.IN to get value.")

        if pin in self.values:
            return self.values[pin]
        return self.LOW
