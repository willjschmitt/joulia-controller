"""Stub interface for the GPIO on a Raspberry Pi board. Provides mocks for the
RPi.GPIO library."""

from enum import Enum


class BoardMode(Enum):
    BOARD = 0
    BCM = 1


class PinState(Enum):
    LOW = False
    HIGH = True


class PinMode(Enum):
    IN = 0
    OUT = 1


class StubGPIO(object):
    """A mock interface to the Raspberry Pi GPIO, mocking the RPi.GPIO library.

    Enforces the use of GPIO constants for setting states like GPIO.LOW, etc...
    """
    LOW = PinState.LOW
    HIGH = PinState.HIGH

    IN = PinMode.IN
    OUT = PinMode.OUT

    BOARD = BoardMode.BOARD
    BCM = BoardMode.BCM

    def __init__(self):
        self.pin_modes = {}
        self.values = {}
        self.board_mode = None

    def setmode(self, board_mode):
        assert board_mode in BoardMode
        self.board_mode = board_mode

    def setup(self, pin, pin_mode):
        assert pin_mode in PinMode
        self.pin_modes[pin] = pin_mode

    def output(self, pin, value):
        assert value in PinState
        if pin not in self.pin_modes:
            raise RuntimeError("Pin mode must be set before setting value.")

        if self.pin_modes[pin] is not self.OUT:
            raise RuntimeError("Pin mode must be StubGPIO.OUT to set value.")

        self.values[pin] = value

    def input(self, pin):
        if pin not in self.pin_modes:
            raise RuntimeError("Pin mode must be set before setting value.")

        if self.pin_modes[pin] is not self.IN:
            raise RuntimeError("Pin mode must be StubGPIO.IN to get value.")

        if pin in self.values:
            return self.values[pin]
        else:
            return self.LOW
