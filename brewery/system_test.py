"""Tests for the brewery.system module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import json
import unittest
from unittest.mock import Mock
from tornado.httpclient import HTTPError

from brewery.brewhouse import Brewhouse
from brewery.system import SimulatedSystem
from brewery.system import System
from http_codes import HTTP_TIMEOUT
from joulia_webserver.models import MashProfile
from joulia_webserver.models import MashStep
from joulia_webserver.models import Recipe
from joulia_webserver.models import RecipeInstance
from measurement.analog_reader import MCP3004AnalogReader
from testing.stub_async_http_client import StubAsyncHTTPClient
from testing.stub_gpio import StubGPIO
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient
from testing.stub_mcp3008 import StubSpiDev
from testing.stub_mcp3008 import StubMCP3008

# TODO(willjschmitt): Python 3.4 does not support HTTPStatus, so we mock it up
# for now, since it's only used for testing.
# from http import HTTPStatus
HTTPStatus = Mock()  # pylint: disable=invalid-name
HTTPStatus.INTERNAL_SERVER_ERROR = 500


class StubUpdateManager(object):
    def watch(self):
        pass

    def stop(self):
        pass


class StubClock(object):
    def __init__(self):
        self._time_counter = -1.0

    def time(self):
        self._time_counter += 1.0
        return float(self._time_counter)


class TestSystem(unittest.TestCase):
    """Tests for the system class."""

    def setUp(self):
        self.http_client = StubJouliaHTTPClient("http://fake-address")
        recipe_instance_pk = 0
        recipe_pk = 0
        self.http_client.recipe_instance = RecipeInstance(
            recipe_instance_pk, recipe_pk)
        with open('testing/brewhouse.json') as brewhouse_file:
            self.http_client.brewhouse = json.load(brewhouse_file)
        strike_temperature = 162.0
        mashout_temperature = 170.0
        mashout_time = 15.0 * 60.0
        boil_time = 60.0 * 60.0
        cool_temperature = 70.0
        mash_temperature_profile = []
        volume = 5.0
        pre_boil_volume_gallons = 6.0
        post_boil_volume_gallons = 5.1
        self.http_client.recipe = Recipe(
            recipe_pk, strike_temperature, mashout_temperature, mashout_time,
            boil_time, cool_temperature, mash_temperature_profile, volume,
            pre_boil_volume_gallons, post_boil_volume_gallons)
        self.ws_client = StubJouliaWebsocketClient(
            "ws://fake-address", self.http_client)
        self.start_stop_client = StubAsyncHTTPClient()

        brewhouse_id = 0

        mcp = StubMCP3008(spi=StubSpiDev())
        analog_reference = 3.3  # Volts
        analog_reader = MCP3004AnalogReader(mcp, analog_reference)

        gpio = StubGPIO()

        self.update_manager = StubUpdateManager()

        self.system = System(self.http_client, self.ws_client,
                             self.start_stop_client, brewhouse_id,
                             analog_reader, gpio, self.update_manager)

    def test_create_brewhouse_succeeds(self):
        self.system.create_brewhouse(0)
        self.assertIsInstance(self.system.brewhouse, Brewhouse)

    def test_end_brewing(self):
        self.system.create_brewhouse(0)
        self.system.end_brewing()

    def test_watch_for_start(self):
        self.start_stop_client.responses = [
            {
                'response': {"recipe_instance": 11},
            },
            None,
        ]
        self.system.watch_for_start()
        self.assertEqual(self.system.brewhouse.recipe_instance, 11)

    def test_watch_for_start_error(self):
        self.start_stop_client.responses = [
            {
                'status_code': HTTPStatus.INTERNAL_SERVER_ERROR,
                'error': HTTPError(HTTPStatus.INTERNAL_SERVER_ERROR),
                'response': None,
            },
        ]
        with self.assertRaises(HTTPError):
            self.system.watch_for_start()

    def test_watch_for_start_timeout(self):
        self.start_stop_client.responses = [
            {
                'status_code': HTTP_TIMEOUT,
                'error': HTTPError(HTTP_TIMEOUT),
                'response': None,
            },
            {
                'response': {"recipe_instance": 11},
            },
            None,
        ]
        self.system.watch_for_start()
        self.assertEqual(self.system.brewhouse.recipe_instance, 11)

    def test_watch_for_end(self):
        self.start_stop_client.responses = [
            {
                'response': {},
            },
            None,
        ]
        self.system.create_brewhouse(0)
        self.system.watch_for_end()

    def test_watch_for_end_error(self):
        self.start_stop_client.responses = [
            {
                'status_code': HTTPStatus.INTERNAL_SERVER_ERROR,
                'error': HTTPError(HTTPStatus.INTERNAL_SERVER_ERROR),
                'response': None,
            }
        ]
        self.system.create_brewhouse(0)
        with self.assertRaises(HTTPError):
            self.system.watch_for_start()

    def test_watch_for_end_timeout(self):
        self.start_stop_client.responses = [
            {
                'status_code': HTTP_TIMEOUT,
                'error': HTTPError(HTTP_TIMEOUT),
                'response': None,
            },
            {
                'response': {},
            },
            None,
        ]
        self.system.create_brewhouse(0)
        self.system.watch_for_end()


class TestSimulatedSystem(unittest.TestCase):
    """Tests for the SimulatedSystem class."""

    def setUp(self):
        self.http_client = StubJouliaHTTPClient("http://fake-address")
        recipe_instance_pk = 0
        recipe_pk = 0
        self.http_client.recipe_instance = RecipeInstance(
            recipe_instance_pk, recipe_pk)
        with open('testing/brewhouse.json') as brewhouse_file:
            self.http_client.brewhouse = json.load(brewhouse_file)
        strike_temperature = 162.0
        mashout_temperature = 170.0
        mashout_time = 15.0 * 60.0
        boil_time = 60.0 * 60.0
        cool_temperature = 70.0
        mash_temperature_profile = MashProfile([MashStep(15*60, 155.0)])
        volume = 5.0
        pre_boil_volume_gallons = 6.0
        post_boil_volume_gallons = 5.1
        self.http_client.recipe = Recipe(
            recipe_pk, strike_temperature, mashout_temperature,
            mashout_time,
            boil_time, cool_temperature, mash_temperature_profile, volume,
            pre_boil_volume_gallons, post_boil_volume_gallons)
        self.ws_client = StubJouliaWebsocketClient(
            "ws://fake-address", self.http_client)
        self.start_stop_client = StubAsyncHTTPClient()

        brewhouse_id = 0

        mcp = StubMCP3008(spi=StubSpiDev())
        analog_reference = 3.3  # Volts
        analog_reader = MCP3004AnalogReader(mcp, analog_reference)

        gpio = StubGPIO()

        self.update_manager = StubUpdateManager()

        self.system = SimulatedSystem(self.http_client, self.ws_client,
                                      self.start_stop_client, brewhouse_id,
                                      analog_reader, gpio, self.update_manager,
                                      clock=StubClock())

    def test_solve_simulation_boil(self):
        # Scaffolds up a new brewhouse ready for simulation without starting the
        # timers.
        recipe_instance = 1
        self.system.create_brewhouse(recipe_instance)
        self.system.start_brewing()
        self.system.brewhouse.state.set_state_by_name('StateBoil')

        self.assertAlmostEqual(self.system.boil_kettle_temperature, 68.0)
        self.assertAlmostEqual(self.system.mash_tun_temperature, 68.0)

        # 5 gallons at ~1deg/gallon/sec is 12deg after ~60sec. This is a rough
        # number rather than an exact one.
        for _ in range(60):
            self.system.brewhouse.task00()
            self.system.solve_simulation()

        self.assertAlmostEqual(self.system.boil_kettle_temperature, 75.5, 1)
        self.assertAlmostEqual(self.system.mash_tun_temperature, 68.0)

    def test_solve_simulation_mash(self):
        # Scaffolds up a new brewhouse ready for simulation without starting the
        # timers.
        recipe_instance = 1
        self.system.create_brewhouse(recipe_instance)
        self.system.start_brewing()
        self.system.brewhouse.state.set_state_by_name('StateMash')

        # Give some gradient from the boil kettle for pushing energy into the
        # mash tun.
        self.system.boil_kettle_temperature = 155.0
        self.assertAlmostEqual(self.system.boil_kettle_temperature, 155.0)
        self.assertAlmostEqual(self.system.mash_tun_temperature, 68.0)

        # 5 gallons at ~1deg/gallon/sec is 12deg after ~60sec. This is a rough
        # number rather than an exact one.
        for _ in range(60):
            self.system.brewhouse.task00()
            self.system.solve_simulation()

        self.assertAlmostEqual(self.system.boil_kettle_temperature, 162.49, 1)
        self.assertAlmostEqual(self.system.mash_tun_temperature, 68.02, 2)
