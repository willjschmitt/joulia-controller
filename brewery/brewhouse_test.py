"""Tests for the brewhouse module."""

import unittest

from brewery.brewhouse import Brewhouse
from brewery.pump import SimplePump
from brewery.vessels import HeatedVessel
from brewery.vessels import HeatExchangedVessel
from measurement.gpio import OutputPin
from testing.stub_arduino import StubAnalogReader
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient
from testing.stub_rtd_sensor import StubRtdSensor


class TestBrewhouse(unittest.TestCase):
    """Tests for the Brewhouse class."""

    def setUp(self):
        self.gpio = StubGPIO()
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)
        recipe_instance = 0
        i2c_bus = None
        i2c_address = 0x0A
        self.analog_reader = StubAnalogReader(i2c_bus, i2c_address)

        stub_gpio = StubGPIO()

        boil_kettle_heating_element_rating = 5500.0
        boil_kettle_volume = 5.0
        boil_kettle_temperature_sensor = StubRtdSensor(70.0)
        boil_kettle_heating_pin = OutputPin(stub_gpio, 0)
        self.boil_kettle = HeatedVessel(
            self.ws_client, recipe_instance, boil_kettle_heating_element_rating,
            boil_kettle_volume, boil_kettle_temperature_sensor,
            boil_kettle_heating_pin)

        mash_tun_volume = 5.0
        mash_tun_temperature_sensor = StubRtdSensor(70.0)
        self.mash_tun = HeatExchangedVessel(
            self.ws_client, recipe_instance, mash_tun_volume,
            mash_tun_temperature_sensor)

        pump_pin = OutputPin(stub_gpio, 1)
        self.main_pump = SimplePump(pump_pin)

        self.brewhouse = Brewhouse(
            self.ws_client, self.gpio, self.analog_reader, recipe_instance,
            self.boil_kettle, self.mash_tun, self.main_pump)

    def test_start_brewing_succeeds(self):
        self.brewhouse.start_brewing()
        # TODO(will): Add checks here

    def test_initialize_recipe_succeeds(self):
        self.brewhouse.initialize_recipe()
        # TODO(will): Add checks here

    def test_start_timers(self):
        self.brewhouse.start_timers()
        # TODO(will): Add checks here

    def test_stop_timers(self):
        self.brewhouse.start_timers()
        self.brewhouse.cancel_timers()
        # TODO(will): Add checks here

    def test_task00(self):
        self.brewhouse.task00()
        # TODO(will): Add checks here

    def test_state_prestart(self):
        self.brewhouse.state.set_state_by_name("StatePrestart")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.enabled)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_premash(self):
        self.brewhouse.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 70.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.enabled)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_premash_not_ready(self):
        self.brewhouse.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 70.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_premash_ready(self):
        self.brewhouse.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 171.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_strike(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.state.set_state_by_name("StateStrike")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.enabled)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEquals(
            self.brewhouse.boil_kettle.temperature_set_point, 155.0, 9)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_post_strike(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.enabled)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEquals(
            self.brewhouse.boil_kettle.temperature_set_point, 155.0, 9)

    def test_state_post_strike_not_ready(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 100.0
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_post_strike_ready(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 156.0
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_mash(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.working_time = 0
        self.brewhouse.state.set_state_by_name("StateMash")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.enabled)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertTrue(self.brewhouse.mash_tun.enabled)

    def test_state_mash_timer_start(self):
        self.brewhouse.mash_tun.temperature_profile = [(15.0, 155.0)]
        self.brewhouse.working_time = 0
        self.brewhouse.state.set_state_by_name("StateMash")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.state.evaluate()
        self.assertAlmostEquals(self.brewhouse.timer, 15.0, 9)
