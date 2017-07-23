"""Tests for the main module."""

import unittest
from http import HTTPStatus

from tornado.httpclient import HTTPError

from brewery.brewhouse import Brewhouse
from http_codes import HTTP_TIMEOUT
from joulia_webserver.models import Recipe
from joulia_webserver.models import RecipeInstance
from main import System
from testing.stub_async_http_client import StubAsyncHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestMain(unittest.TestCase):
    """Tests for the main function."""
    pass


class TestCreateBrewhouse(unittest.TestCase):
    """Tests for the create_brewhouse function."""

    def setUp(self):
        self.http_client = StubJouliaHTTPClient("http://fake-address")
        recipe_instance_pk = 0
        recipe_pk = 0
        self.http_client.recipe_instance = RecipeInstance(
            recipe_instance_pk, recipe_pk)
        strike_temperature = 162.0
        mashout_temperature = 170.0
        mashout_time = 15.0 * 60.0
        boil_time = 60.0 * 60.0
        cool_temperature = 70.0
        mash_temperature_profile = []
        self.http_client.recipe = Recipe(
            recipe_pk, strike_temperature, mashout_temperature, mashout_time,
            boil_time, cool_temperature, mash_temperature_profile)
        self.ws_client = StubJouliaWebsocketClient(
            "ws://fake-address", self.http_client)
        self.start_stop_client = StubAsyncHTTPClient()
        brewhouse_id = 0
        self.system = System(self.http_client, self.ws_client,
                             self.start_stop_client, brewhouse_id)

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
        self.assertEquals(self.system.brewhouse.recipe_instance, 11)

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
        self.assertEquals(self.system.brewhouse.recipe_instance, 11)

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
