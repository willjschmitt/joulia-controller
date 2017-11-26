"""Tests for the vessesls module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest
from unittest.mock import Mock

from brewery.vessels import HeatedVessel
from brewery.vessels import HeatExchangedVessel
from brewery.vessels import SimpleVessel
from brewery.vessels import TemperatureMonitoredVessel
from measurement.gpio import OutputPin
from testing.stub_analog_reader import StubAnalogReader
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
        self.assertAlmostEqual(self.vessel.volume, volume)


class TestTemperatureMonitoredVessel(unittest.TestCase):
    """Tests for the TemperatureMonitoredVessel class."""

    def setUp(self):
        volume = 5.0
        self.temperature_sensor = StubRtdSensor(68.0)
        self.vessel = TemperatureMonitoredVessel(
            volume, self.temperature_sensor)

    def test_measure_temperature(self):
        self.assertEqual(self.temperature_sensor.measure_calls, 0)
        self.vessel.measure_temperature()
        self.assertEqual(self.temperature_sensor.measure_calls, 1)

    def test_temperature(self):
        self.temperature_sensor.temperature = 70.0
        self.assertAlmostEqual(self.vessel.temperature, 70.0, 9)


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
        self.assertAlmostEqual(self.vessel.temperature_set_point, 70.0, 9)

    def test_disable(self):
        self.vessel.disable()
        self.assertFalse(self.vessel.element_status)
        self.assertEqual(self.vessel.heating_pin.value, self.gpio.LOW)

    def test_enable(self):
        self.vessel.enable()
        self.assertTrue(self.vessel.element_status)

    def test_turn_off(self):
        self.vessel.enable()
        self.vessel.turn_off()
        self.assertEqual(self.vessel.heating_pin.value, self.gpio.LOW)

    def test_turn_on_enabled(self):
        self.vessel.enable()
        self.vessel.turn_on()
        self.assertEqual(self.vessel.heating_pin.value, self.gpio.HIGH)

    def test_turn_on_disabled(self):
        self.vessel.disable()
        self.vessel.turn_on()
        self.assertEqual(self.vessel.heating_pin.value, self.gpio.LOW)

    def test_turn_on_with_emergency_stop(self):
        self.vessel.emergency_stop = True
        self.vessel.enable()
        self.vessel.turn_on()
        self.assertEqual(self.vessel.heating_pin.value, self.gpio.LOW)

    def test_set_liquid_level(self):
        self.vessel.set_liquid_level(5.0)
        proportional_gain = self.vessel.regulator.gain_proportional
        integral_gain = self.vessel.regulator.gain_integral
        self.vessel.set_liquid_level(10.0)
        self.assertAlmostEqual(self.vessel.regulator.gain_proportional,
                               proportional_gain * 2.0, 9)
        self.assertAlmostEqual(self.vessel.regulator.gain_integral,
                               integral_gain * 2.0, 9)

    @staticmethod
    def get_mock_periodic_callback():
        timer = Mock()
        timer.callback_time = 1000
        timer._next_timeout = 1.0  # pylint: disable=protected-access
        return timer

    def test_regulate_okay(self):
        self.vessel.set_temperature(70.0)
        self.temperature_sensor.temperature = 70.0
        timer = self.get_mock_periodic_callback()
        self.vessel.regulate(timer)
        self.assertAlmostEqual(self.vessel.duty_cycle, 0.0, 9)

    def test_regulate_full_power(self):
        self.vessel.set_temperature(70.0)
        self.temperature_sensor.temperature = 0.0
        self.vessel.enable()
        timer = self.get_mock_periodic_callback()
        self.vessel.regulate(timer)
        self.assertAlmostEqual(self.vessel.duty_cycle, 1.0, 9)

    def test_schedule_heating_element_always_off(self):
        self.vessel.duty_cycle = 0.0
        timer = self.get_mock_periodic_callback()
        timeouts = self.vessel.schedule_heating_element(timer)
        self.assertEqual(len(timeouts), 1)
        turn_off = timeouts[0]
        self.assertEqual(turn_off.deadline, 1.0)

    def test_schedule_heating_element_always_on(self):
        self.vessel.duty_cycle = 1.0
        timer = self.get_mock_periodic_callback()
        timeouts = self.vessel.schedule_heating_element(timer)
        self.assertEqual(len(timeouts), 1)
        turn_on = timeouts[0]
        self.assertEqual(turn_on.deadline, 1.0)

    def test_schedule_heating_element_switched_time(self):
        self.vessel.duty_cycle = 0.6
        timer = self.get_mock_periodic_callback()
        timeouts = self.vessel.schedule_heating_element(timer)
        self.assertEqual(len(timeouts), 2)
        turn_on = timeouts[0]
        turn_off = timeouts[1]
        self.assertEqual(turn_on.deadline, 1.0)
        self.assertEqual(turn_off.deadline, 1.0 + 600)

    def test_power_zero(self):
        self.vessel.duty_cycle = 0.0
        self.vessel.rating = 5500.0
        self.vessel.enable()
        self.assertAlmostEqual(self.vessel.power, 0.0, 9)

    def test_power_full(self):
        self.vessel.duty_cycle = 1.0
        self.vessel.rating = 5500.0
        self.vessel.enable()
        self.assertAlmostEqual(self.vessel.power, 5500.0, 9)

    def test_temperature_ramp(self):
        self.vessel.duty_cycle = 1.0
        self.vessel.rating = 5500.0
        self.vessel.set_liquid_level(1.0)
        self.vessel.enable()
        # 0.62 is the rate the temperature should increase with 1gal.
        # 5500W -> 0.62 degF/1gal/second
        self.assertAlmostEqual(self.vessel.temperature_ramp, 0.62, 2)

    def test_from_json(self):
        analog_reader = StubAnalogReader()
        configuration = {
            "temperature_sensor": {
                "analog_pin": 0,
                "tau_filter": 10.0,
                "analog_reference": 3.3,
                "rtd": {
                    "alpha": 0.00385,
                    "zero_resistance": 100.0,
                },
                "amplifier": {
                    "vcc": 3.3,
                    "rtd_top_resistance": 1000.0,
                    "amplifier_resistance_a": 15000.0,
                    "amplifier_resistance_b": 270000.0,
                    "offset_resistance_bottom": 10000.0,
                    "offset_resistance_top": 100000.0,
                }
            },
            "heating_element": {
                "rating": 5500.0,
                "pin": 27,
            },
            "volume": 5.0,
        }
        HeatedVessel.from_json(self.ws_client, self.gpio, analog_reader,
                               self.recipe_instance, configuration)


class TestHeatExchangedVessel(unittest.TestCase):
    """Tests for the HeadExchangedVessel class."""

    def setUp(self):
        self.recipe_instance = 0
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)
        volume = 5.0
        self.temperature_sensor = StubRtdSensor(70.0)
        self.vessel = HeatExchangedVessel(self.ws_client, self.recipe_instance,
                                          volume, self.temperature_sensor)

    def test_recalculate_gains(self):
        self.vessel.volume = 1.0
        self.vessel.heat_exchanger_conductivity = 1.0

        self.vessel.recalculate_gains()
        self.assertAlmostEqual(self.vessel.regulator.gain_proportional, 0.2, 9)
        self.assertAlmostEqual(self.vessel.regulator.gain_integral, 0.002, 9)

        self.vessel.volume = 2.0
        self.vessel.recalculate_gains()
        self.assertAlmostEqual(self.vessel.regulator.gain_proportional, 0.4, 9)
        self.assertAlmostEqual(self.vessel.regulator.gain_integral, 0.004, 9)

    def test_enable(self):
        self.vessel.enable()
        self.assertTrue(self.vessel.enabled)

    def test_disable(self):
        self.vessel.disable()
        self.assertFalse(self.vessel.enabled)

    def test_turn_on_with_emergency_stop(self):
        self.vessel.emergency_stop = True
        self.vessel.enable()
        self.assertFalse(self.vessel.enabled)

    def test_set_liquid_level(self):
        self.vessel.volume = 1.0
        self.vessel.heat_exchanger_conductivity = 1.0
        self.vessel.recalculate_gains()
        self.assertAlmostEqual(self.vessel.regulator.gain_proportional, 0.2, 9)
        self.assertAlmostEqual(self.vessel.regulator.gain_integral, 0.002, 9)

        self.vessel.set_liquid_level(2.0)
        self.assertAlmostEqual(self.vessel.regulator.gain_proportional, 0.4, 9)
        self.assertAlmostEqual(self.vessel.regulator.gain_integral, 0.004, 9)

    def test_regulate_none(self):
        self.temperature_sensor.temperature = 70.0
        self.vessel.set_temperature(70.0)
        self.vessel.enable()
        self.vessel.regulate()
        self.assertAlmostEqual(self.vessel.source_temperature, 70.0, 9)

    def test_regulate_full(self):
        self.temperature_sensor.temperature = 70.0
        self.vessel.set_temperature(212.0)
        self.vessel.enable()
        self.vessel.regulate()
        self.assertAlmostEqual(self.vessel.source_temperature, 85.0, 9)

    def test_temperature_ramp_enabled(self):
        self.vessel.source_temperature = 200.0
        self.temperature_sensor.temperature = 100.0
        self.vessel.volume = 1.0
        self.vessel.heat_exchanger_conductivity = 1.0  # W/delta degF
        self.vessel.enable()
        # 100degF delta with heat_exchanger_conductivity = 1 -> 100W.
        # 100W is 0.0112 degF/second for water.
        self.assertAlmostEqual(self.vessel.temperature_ramp, 0.0113, 2)

    def test_temperature_ramp_disabled(self):
        self.vessel.source_temperature = 200.0
        self.temperature_sensor.temperature = 100.0
        self.vessel.volume = 1.0
        self.vessel.heat_exchanger_conductivity = 1.0  # W/delta degF
        self.vessel.disable()
        # 100degF delta with heat_exchanger_conductivity = 1 -> 100W.
        # 100W is 0.0112 degF/second for water.
        self.assertAlmostEqual(self.vessel.temperature_ramp, 0.0, 9)

    def test_from_json(self):
        analog_reader = StubAnalogReader()
        configuration = {
            "temperature_sensor": {
                "analog_pin": 1,
                "tau_filter": 10.0,
                "analog_reference": 3.3,
                "rtd": {
                    "alpha": 0.00385,
                    "zero_resistance": 100.0,
                },
                "amplifier": {
                    "vcc": 3.3,
                    "rtd_top_resistance": 1000.0,
                    "amplifier_resistance_a": 15000.0,
                    "amplifier_resistance_b": 2700000.0,
                    "offset_resistance_bottom": 10000.0,
                    "offset_resistance_top": 100000.0,
                },
            },
            "volume": 5.0,
            "heat_exchanger_conductivity": 1.0,
        }
        HeatExchangedVessel.from_json(self.ws_client, analog_reader,
                                      self.recipe_instance, configuration)
