"""The system handling for a Joulia brewhouse.

Handles connections and initialization of systems. Monitors for start/stops to
wrap the Brewhouse and keep it scoped to brewing while this System handles
process.
"""
import logging
import os
from urllib.parse import urlencode

from tornado import ioloop
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient

from brewery.brewhouse import Brewhouse
from git import Repo
from http_codes import HTTP_TIMEOUT
from joulia_webserver.client import JouliaHTTPClient
from joulia_webserver.client import JouliaWebsocketClient
import settings
from update import UpdateManager

LOGGER = logging.getLogger(__name__)

# Rate to check for updates. Set to 30 seconds.
UPDATE_CHECK_RATE = 30 * 1000  # milliseconds


class System(object):
    """A brewhouse system monitoring for connections and checking for updates.
    """
    def __init__(self, http_client, ws_client, start_stop_client, brewhouse_id,
                 analog_reader, gpio, update_manager):
        self.http_client = http_client
        self.ws_client = ws_client
        self.start_stop_client = start_stop_client
        self.brewhouse = None
        self.brewhouse_id = brewhouse_id
        self.analog_reader = analog_reader
        self.gpio = gpio
        self.update_manager = update_manager

        # Check for new versions periodically. Timers get turned on and off by
        # the recipe start/stop watchers.
        self.update_check_timer = ioloop.PeriodicCallback(
            self.update_manager.check_version, UPDATE_CHECK_RATE)
        self.update_check_timer.start()

    @classmethod
    def create_from_settings(cls, analog_reader, gpio):
        """Creates a System using values from settings.

        Only needs the I/O interfaces to be able to control the simulated
        version.
        """
        LOGGER.info('Starting brewery.')
        http_client = JouliaHTTPClient(
            settings.HTTP_PREFIX + "://" + settings.HOST,
            auth_token=settings.AUTHTOKEN)
        ws_address = "{}://{}/live/timeseries/socket/".format(
            settings.WS_PREFIX, settings.HOST)
        ws_client = JouliaWebsocketClient(ws_address, http_client,
                                          auth_token=settings.AUTHTOKEN)
        start_stop_client = AsyncHTTPClient()

        brewhouse_id = http_client.get_brewhouse_id()

        repo = Repo(os.getcwd())
        update_manager = UpdateManager(repo, http_client)
        system = System(http_client, ws_client, start_stop_client, brewhouse_id,
                        analog_reader, gpio, update_manager)
        system.watch_for_start()
        LOGGER.info("Brewery initialized.")

        ioloop.IOLoop.instance().start()

    def create_brewhouse(self, recipe_instance_pk):
        """Creates a new brewhouse instance when starting a new recipe."""
        LOGGER.info("Creating brewhouse with recipe instance %s.",
                    recipe_instance_pk)

        recipe_instance = self.http_client.get_recipe_instance(
            recipe_instance_pk)
        recipe = self.http_client.get_recipe(recipe_instance.recipe_pk)

        configuration = self.http_client.get_brewhouse(self.brewhouse_id)

        brewhouse = Brewhouse.from_json(
            self.ws_client, self.gpio, self.analog_reader, recipe_instance_pk,
            recipe, configuration)

        self.brewhouse = brewhouse

    def watch_for_start(self):
        """Makes a long-polling request to joulia-webserver to check
        if the server received a request to start a brewing session.

        Once the request completes, the internal method
        handle_start_request is executed.
        """

        def handle_start_request(response):
            """Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the startup
            logic for this Brewhouse
            """
            if response.error:
                if response.code == HTTP_TIMEOUT:
                    LOGGER.warning("Lost connection to server. Retrying...")
                    self.watch_for_start()
                else:
                    LOGGER.error(response)
                    response.rethrow()
            else:
                LOGGER.info("Got command to start brewing session.")
                response = json_decode(response.body)
                recipe_instance = response['recipe_instance']
                # Cancel checking for updates when starting a brew session.
                self.update_check_timer.stop()
                self.create_brewhouse(recipe_instance)
                self.brewhouse.start_brewing()
                self.watch_for_end()

        LOGGER.info("Watching for recipe instance start on brewhouse %s.",
                    self.brewhouse_id)
        post_data = {'brewhouse': self.brewhouse_id}
        uri = "{}://{}/live/recipeInstance/start/".format(
            settings.HTTP_PREFIX, settings.HOST)
        self.start_stop_client.fetch(
            uri, handle_start_request, method="POST", body=urlencode(post_data),
            headers={'Authorization': 'Token {}'.format(settings.AUTHTOKEN)})

    def watch_for_end(self):
        """Makes a long-polling request to joulia-webserver to check
        if the server received a request to end the brewing session.

        Once the request completes, the internal method
        handle_end_request is executed.
        """

        def handle_end_request(response):
            """Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the termination
            logic for this Brewhouse
            """
            if response.error:
                if response.code == HTTP_TIMEOUT:
                    LOGGER.warning("Lost connection to server. Retrying...")
                    self.watch_for_end()
                else:
                    LOGGER.error(response)
                    response.rethrow()
            else:
                LOGGER.info("Got command to end brewing session.")
                self.end_brewing()

                # Check for updates while not running a brew session.
                self.update_check_timer.start()

                self.watch_for_start()

        LOGGER.info("Watching for recipe instance end on brewhouse %s.",
                    self.brewhouse_id)
        post_data = {'brewhouse': self.brewhouse_id}
        uri = "{}://{}/live/recipeInstance/end/".format(
            settings.HTTP_PREFIX, settings.HOST)
        self.start_stop_client.fetch(
            uri, handle_end_request, method="POST", body=urlencode(post_data),
            headers={'Authorization': 'Token {}'.format(settings.AUTHTOKEN)})

    def end_brewing(self):
        """Ends the brewing session by canceling all timers on the brewhouse."""
        self.brewhouse.cancel_timers()