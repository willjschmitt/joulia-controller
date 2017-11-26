"""Tests for the brewhouse module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from brewery.brewhouse import Brewhouse
from brewery.pump import SimplePump
from brewery.vessels import HeatExchangedVessel
from brewery.vessels import HeatedVessel
from joulia_webserver.models import MashProfile
from joulia_webserver.models import MashStep
from joulia_webserver.models import Recipe
from measurement.gpio import OutputPin
from testing.stub_analog_reader import StubAnalogReader
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
        self.recipe_instance = 0
        self.analog_reader = StubAnalogReader()

        stub_gpio = StubGPIO()

        heating_element_rating = 5500.0
        boil_kettle_volume = 5.0
        boil_kettle_temperature_sensor = StubRtdSensor(70.0)
        boil_kettle_heating_pin = OutputPin(stub_gpio, 0)
        self.boil_kettle = HeatedVessel(
            self.ws_client, self.recipe_instance,
            heating_element_rating, boil_kettle_volume,
            boil_kettle_temperature_sensor, boil_kettle_heating_pin)

        mash_tun_volume = 5.0
        mash_tun_temperature_sensor = StubRtdSensor(70.0)
        self.mash_tun = HeatExchangedVessel(
            self.ws_client, self.recipe_instance, mash_tun_volume,
            mash_tun_temperature_sensor)

        pump_pin = OutputPin(stub_gpio, 1)
        self.main_pump = SimplePump(self.ws_client, self.recipe_instance, pump_pin)

        recipe_pk = 3
        strike_temperature = 170.0
        mashout_temperature = 170.0
        mashout_time = 15.0 * 60.0
        boil_time = 60.0 * 60.0
        cool_temperature = 70.0
        mash_temperature_profile = MashProfile([])
        self.recipe = Recipe(
            recipe_pk, strike_temperature, mashout_temperature, mashout_time,
            boil_time, cool_temperature, mash_temperature_profile)

        self.brewhouse = Brewhouse(
            self.ws_client, self.recipe_instance, self.boil_kettle,
            self.mash_tun, self.main_pump, self.recipe)

    def test_start_brewing_succeeds(self):
        self.brewhouse.start_brewing()
        # TODO(will): Add checks here

    def test_start_timers(self):
        self.brewhouse.start_timers()
        # TODO(will): Add checks here

    def test_stop_timers(self):
        self.brewhouse.start_timers()
        self.brewhouse.cancel_timers()
        # TODO(will): Add checks here

    def test_task00(self):
        self.brewhouse.start_timers()
        self.brewhouse.task00()
        # TODO(will): Add checks here

    def test_state_prestart(self):
        self.brewhouse.state.set_state_by_name("StatePrestart")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_premash(self):
        self.brewhouse.recipe.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 70.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_premash_not_ready(self):
        self.brewhouse.recipe.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 70.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_premash_ready(self):
        self.brewhouse.recipe.strike_temperature = 170.0
        self.boil_kettle.temperature_sensor.temperature = 171.0
        self.brewhouse.state.set_state_by_name("StatePremash")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_strike(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.state.set_state_by_name("StateStrike")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEqual(
            self.brewhouse.boil_kettle.temperature_set_point, 155.0, 9)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_post_strike(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEqual(
            self.brewhouse.boil_kettle.temperature_set_point, 155.0, 9)

    def test_state_post_strike_not_ready(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 100.0
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_post_strike_ready(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 156.0
        self.brewhouse.state.set_state_by_name("StatePostStrike")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_mash(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.working_time = 0
        self.brewhouse.state.set_state_by_name("StateMash")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertTrue(self.brewhouse.mash_tun.enabled)

    def test_state_mash_timer_start(self):
        self.brewhouse.recipe.mash_temperature_profile = MashProfile([
            MashStep(15.0, 155.0),
        ])
        self.brewhouse.working_time = 0
        self.brewhouse.state.set_state_by_name("StateMash")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.state.evaluate()
        self.assertAlmostEqual(self.brewhouse.timer, 15.0, 9)

    def test_state_mashout_ramp(self):
        self.brewhouse.state.set_state_by_name("StateMashoutRamp")
        self.brewhouse.working_time = 0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.recipe.mashout_temperature = 170.0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEqual(
            self.brewhouse.mash_tun.temperature_set_point, 170.0, 9)
        self.assertAlmostEqual(
            self.brewhouse.boil_kettle.temperature_set_point, 175.0, 9)

    def test_state_mashout_ramp_high_enough_temp(self):
        self.brewhouse.state.set_state_by_name("StateMashoutRamp")
        self.brewhouse.working_time = 0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.recipe.mashout_temperature = 170.0
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 171.0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

        self.assertEqual(self.brewhouse.state.state.__class__.__name__,
                         "StateMashoutRecirculation")

    def test_state_mashout_recirculation(self):
        self.brewhouse.state.set_state_by_name("StateMashoutRecirculation")
        self.brewhouse.working_time = 0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.recipe.mashout_temperature = 170.0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEqual(
            self.brewhouse.mash_tun.temperature_set_point, 170.0, 9)
        self.assertAlmostEqual(
            self.brewhouse.boil_kettle.temperature_set_point, 170.0, 9)

    def test_state_mashout_recirculation_timer_start(self):
        self.brewhouse.state.set_state_by_name("StateMashoutRecirculation")
        self.brewhouse.working_time = 0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.recipe.mashout_time = 15.0
        self.brewhouse.state.evaluate()
        self.assertAlmostEqual(self.brewhouse.timer, 15.0, 9)
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_mashout_recirculation_timer_done(self):
        self.brewhouse.state.set_state_by_name("StateMashoutRecirculation")
        self.brewhouse.working_time = 16.0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.recipe.mashout_time = 15.0
        self.brewhouse.state.evaluate()
        self.assertAlmostEqual(self.brewhouse.timer, -1.0, 9)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_sparge_prep(self):
        self.brewhouse.state.set_state_by_name("StateSpargePrep")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_sparge(self):
        self.brewhouse.state.set_state_by_name("StateSparge")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_pre_boil(self):
        self.brewhouse.state.set_state_by_name("StatePreBoil")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_mash_to_boil(self):
        self.brewhouse.state.set_state_by_name("StateMashToBoil")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_boil_preheat(self):
        self.brewhouse.state.set_state_by_name("StateBoilPreheat")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_boil_preheat_next_state(self):
        self.brewhouse.state.set_state_by_name("StateBoilPreheat")
        self.brewhouse.recipe.boil_temperature = 210.0
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 201.0
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertEqual(
            self.brewhouse.state.state.__class__.__name__, "StateBoil")

    def test_state_boil(self):
        self.brewhouse.state.set_state_by_name("StateBoil")
        self.brewhouse.recipe.boil_temperature = 210.0
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.working_time = 0
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertTrue(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertAlmostEqual(
            self.brewhouse.boil_kettle.temperature_set_point, 210.0, 9)

    def test_state_boil_not_done(self):
        self.brewhouse.state.set_state_by_name("StateBoil")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.working_time = 0
        self.brewhouse.recipe.boil_time = 60.0
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_boil_done(self):
        self.brewhouse.state.set_state_by_name("StateBoil")
        self.brewhouse.state.state_time_change = 0
        self.brewhouse.working_time = 61.0
        self.brewhouse.recipe.boil_time = 60.0
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)
        self.assertEqual(
            self.brewhouse.state.state.__class__.__name__, "StateCoolingPrep")

    def test_state_cooling_prep(self):
        self.brewhouse.state.set_state_by_name("StateCoolingPrep")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_cool(self):
        self.brewhouse.state.set_state_by_name("StateCool")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)

    def test_state_cool_not_done(self):
        self.brewhouse.state.set_state_by_name("StateCool")
        self.brewhouse.recipe.cool_temperature = 68.0
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 70.0
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.request_permission)

    def test_state_cool_done(self):
        self.brewhouse.state.set_state_by_name("StateCool")
        self.brewhouse.recipe.cool_temperature = 68.0
        self.brewhouse.boil_kettle.temperature_sensor.temperature = 67.0
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_pumpout(self):
        self.brewhouse.state.set_state_by_name("StatePumpout")
        self.brewhouse.state.evaluate()
        self.assertTrue(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertTrue(self.brewhouse.request_permission)

    def test_state_done(self):
        self.brewhouse.state.set_state_by_name("StateDone")
        self.brewhouse.state.evaluate()
        self.assertFalse(self.brewhouse.main_pump.pump_status)
        self.assertFalse(self.brewhouse.boil_kettle.element_status)
        self.assertFalse(self.brewhouse.mash_tun.enabled)
        self.assertFalse(self.brewhouse.request_permission)

    def test_from_json(self):
        configuration = {
            "boil_kettle": {
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
            },
            "mash_tun": {
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
                    }
                },
                "volume": 5.0,
                "heat_exchanger_conductivity": 1.0,
            },
            "main_pump": {
                "pin": 17,
            },
        }
        Brewhouse.from_json(self.ws_client, self.gpio, self.analog_reader,
                            self.recipe_instance, self.recipe, configuration)
