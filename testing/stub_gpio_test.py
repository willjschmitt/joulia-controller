"""Tests for the stub_gpio module."""

import unittest

from testing.stub_gpio import StubGPIO


class TestStubGPIO(unittest.TestCase):
    """Tests for the StubGPIO class."""

    def setUp(self):
        self.gpio = StubGPIO()

    def test_setmode(self):
        self.gpio.setmode(self.gpio.BOARD)
        self.assertIs(self.gpio.BOARD, self.gpio.board_mode)

    def test_setup_input(self):
        self.assertNotIn(1, self.gpio.pin_modes)
        self.gpio.setup(1, self.gpio.IN)
        self.assertIn(1, self.gpio.pin_modes)
        self.assertIs(self.gpio.pin_modes[1], self.gpio.IN)

    def test_setup_output(self):
        self.assertNotIn(1, self.gpio.pin_modes)
        self.gpio.setup(1, self.gpio.OUT)
        self.assertIn(1, self.gpio.pin_modes)
        self.assertIs(self.gpio.pin_modes[1], self.gpio.OUT)

    def test_output(self):
        self.gpio.setup(1, self.gpio.OUT)
        self.gpio.output(1, self.gpio.LOW)
        self.assertIs(self.gpio.values[1], self.gpio.LOW)

    def test_output_not_setup(self):
        with self.assertRaisesRegexp(RuntimeError, "Pin mode must be set"):
            self.gpio.output(1, self.gpio.LOW)

    def test_output_pin_mode_wrong(self):
        self.gpio.setup(1, self.gpio.IN)
        with self.assertRaisesRegexp(
                RuntimeError, "Pin mode must be StubGPIO.OUT"):
            self.gpio.output(1, self.gpio.LOW)

    def test_input(self):
        self.gpio.setup(1, self.gpio.IN)
        self.gpio.values[1] = self.gpio.HIGH
        self.assertIs(self.gpio.input(1), self.gpio.HIGH)

    def test_input_value_not_set(self):
        self.gpio.setup(1, self.gpio.IN)
        self.assertIs(self.gpio.input(1), self.gpio.LOW)

    def test_input_not_setup(self):
        with self.assertRaisesRegexp(RuntimeError, "Pin mode must be set"):
            self.gpio.input(1)

    def test_input_pin_mode_wrong(self):
        self.gpio.setup(1, self.gpio.OUT)
        with self.assertRaisesRegexp(
                RuntimeError, "Pin mode must be StubGPIO.IN"):
            self.gpio.input(1)