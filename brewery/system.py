"""The system handling for a Joulia brewhouse.

Handles connections and initialization of systems. Monitors for start/stops to
wrap the Brewhouse and keep it scoped to brewing while this System handles
process.
"""
import logging
import os
import time
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
from update import GitUpdateManager

LOGGER = logging.getLogger(__name__)


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
        self.update_manager.watch()

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
        update_manager = GitUpdateManager(repo, http_client, brewhouse_id)
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
                self.update_manager.stop()
                self.create_brewhouse(recipe_instance)
                self.start_brewing()
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
                self.update_manager.watch()

                self.watch_for_start()

        LOGGER.info("Watching for recipe instance end on brewhouse %s.",
                    self.brewhouse_id)
        post_data = {'brewhouse': self.brewhouse_id}
        uri = "{}://{}/live/recipeInstance/end/".format(
            settings.HTTP_PREFIX, settings.HOST)
        self.start_stop_client.fetch(
            uri, handle_end_request, method="POST", body=urlencode(post_data),
            headers={'Authorization': 'Token {}'.format(settings.AUTHTOKEN)})

    def start_brewing(self):
        """Kicks brewhouse off to start brewing."""
        self.brewhouse.start_brewing()

    def end_brewing(self):
        """Ends the brewing session by canceling all timers on the brewhouse."""
        self.brewhouse.cancel_timers()


class SimulatedSystem(System):
    """A system with simulation controls for auto-adjusting the temperatures.
    """

    SIMULATION_PERIOD_MILLISECONDS = 1000

    def __init__(self, *args, **kwargs):
        if 'clock' in kwargs:
            clock = kwargs['clock']
            del kwargs['clock']
            self.clock = clock
        else:
            self.clock = time

        super(SimulatedSystem, self).__init__(*args, **kwargs)

        self.simulation_timer = ioloop.PeriodicCallback(
            self.solve_simulation, self.SIMULATION_PERIOD_MILLISECONDS)

        self.last_simulated_time = self.clock.time()
        self.boil_kettle_temperature = 68.0
        self.mash_tun_temperature = 68.0

    def run_simulation(self):
        """Starts the periodic simulation solver timers."""
        LOGGER.info("Starting simulation mode for simulated brewery.")
        self.simulation_timer.start()

    def end_simulation(self):
        """Stops the periodic simulation solver timers."""
        LOGGER.info("Ending simulation mode for simulated brewery.")
        self.simulation_timer.stop()

    def start_brewing(self):
        """Kicks brewhouse off to start brewing along with starting the
        simulation.
        """
        super(SimulatedSystem, self).start_brewing()
        self.run_simulation()

    def solve_simulation(self):
        """Solves the temperatures for the equipment in the brewhouse."""
        current_time = self.clock.time()
        delta_time = current_time - self.last_simulated_time
        self.solve_boil_kettle_temperature(delta_time)
        self.solve_mash_tun_temperature(delta_time)
        self.last_simulated_time = current_time

    def solve_boil_kettle_temperature(self, delta_time):
        """Solves the boil kettle temperature for the brewhouse."""
        ramp = self.brewhouse.boil_kettle.temperature_ramp
        self.boil_kettle_temperature += ramp * delta_time
        temperature_sensor = self.brewhouse.boil_kettle.temperature_sensor
        voltage = temperature_sensor.reverse_temperature(
            self.boil_kettle_temperature)
        self.analog_reader.write_read_voltage(
            temperature_sensor.analog_in_pin, voltage)

    def solve_mash_tun_temperature(self, delta_time):
        """Solves the mash tun temperature for the brewhouse."""
        self.mash_tun_temperature += (
            self.brewhouse.mash_tun.temperature_ramp * delta_time)
        temperature_sensor = self.brewhouse.mash_tun.temperature_sensor
        voltage = temperature_sensor.reverse_temperature(
            self.mash_tun_temperature)
        self.analog_reader.write_read_voltage(
            temperature_sensor.analog_in_pin, voltage)
