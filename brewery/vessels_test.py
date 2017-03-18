"""Tests for the vessesls module."""

import unittest

from brewery.vessels import HeatedVessel
from brewery.vessels import SimpleVessel
from brewery.vessels import TemperatureMonitoredVessel
from measurement.gpio import OutputPin
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient
from testing.stub_rtd_sensor import StubRtdSensor


class TestSimpleVessel(unittest.TestCase):
    """Tests for the SimpleVessel class."""

    def setUp(self):
        volume = 5.0
        self.vessel = SimpleVessel(volume)

    def test_set_liquid_level(self):
        volume = 10.0
        self.vessel.set_liquid_level(volume)
        self.assertAlmostEquals(self.vessel.volume, volume)


class TestTemperatureMonitoredVessel(unittest.TestCase):
    """Tests for the TemperatureMonitoredVessel class."""

    def setUp(self):
        volume = 5.0
        self.temperature_sensor = StubRtdSensor(68.0)
        self.vessel = TemperatureMonitoredVessel(
            volume, self.temperature_sensor)

    def test_measure_temperature(self):
        self.assertEquals(self.temperature_sensor.measure_calls, 0)
        self.vessel.measure_temperature()
        self.assertEquals(self.temperature_sensor.measure_calls, 1)

    def test_temperature(self):
        self.temperature_sensor.temperature = 70.0
        self.assertAlmostEquals(self.vessel.temperature, 70.0, 9)


class TestHeatedVessel(unittest.TestCase):
    """Tests for the HeatedVessel class."""

    def setUp(self):
        self.recipe_instance = 0
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)
        rating = 5500.0
        volume = 5.0
        self.temperature_sensor = StubRtdSensor(70.0)
        self.gpio = StubGPIO()
        self.heating_pin = OutputPin(self.gpio, 0)
        self.vessel = HeatedVessel(
            self.ws_client, self.recipe_instance, rating, volume,
            self.temperature_sensor, self.heating_pin)

    def test_set_temperature(self):
        self.vessel.set_temperature(70.0)
        self.assertAlmostEquals(self.vessel.temperature_set_point, 70.0, 9)

    def test_turn_off(self):
        self.vessel.turn_off()
        self.assertFalse(self.vessel.element_status)
        self.assertEquals(self.vessel.heating_pin.value, self.gpio.LOW)

    def test_turn_on(self):
        self.vessel.turn_on()
        self.assertTrue(self.vessel.element_status)
        self.assertEquals(self.vessel.heating_pin.value, self.gpio.HIGH)

    def test_set_liquid_level(self):
        self.vessel.set_liquid_level(5.0)
        proportional_gain = self.vessel.regulator.gain_proportional
        integral_gain = self.vessel.regulator.gain_integral
        self.vessel.set_liquid_level(10.0)
        self.assertAlmostEquals(self.vessel.regulator.gain_proportional,
                                proportional_gain * 2.0, 9)
        self.assertAlmostEquals(self.vessel.regulator.gain_integral,
                                integral_gain * 2.0, 9)

    def test_regulate_okay(self):
        self.vessel.set_temperature(70.0)
        self.temperature_sensor.temperature = 70.0
        self.vessel.regulate()
        self.assertAlmostEquals(self.vessel.duty_cycle, 0.0, 9)

    def test_regulate_full_power(self):
        self.vessel.set_temperature(70.0)
        self.temperature_sensor.temperature = 0.0
        self.vessel.turn_on()
        self.vessel.regulate()
        self.assertAlmostEquals(self.vessel.duty_cycle, 1.0, 9)

    def test_power_zero(self):
        self.vessel.duty_cycle = 0.0
        self.vessel.rating = 5500.0
        self.vessel.turn_on()
        self.assertAlmostEquals(self.vessel.power, 0.0, 9)

    def test_power_full(self):
        self.vessel.duty_cycle = 1.0
        self.vessel.rating = 5500.0
        self.vessel.turn_on()
        self.assertAlmostEquals(self.vessel.power, 5500.0, 9)

    def test_temperature_ramp(self):
        self.vessel.duty_cycle = 1.0
        self.vessel.rating = 5500.0
        self.vessel.set_liquid_level(1.0)
        self.vessel.turn_on()
        # 0.62 is the rate the temperature should increase with 1gal.
        # 5500W -> 0.62 degF/1gal/second
        self.assertAlmostEquals(self.vessel.temperature_ramp, 0.62, 2)
