"""Main code for launching a Brewhouse joulia-controller."""
import json
import logging.config
try:
    import RPi.GPIO as gpio
except (ImportError, RuntimeError):
    # TODO(will): Come up with a better hack for working on non-Raspberry Pi
    # systems.
    from testing.stub_gpio import StubGPIO
    gpio = StubGPIO()
try:
    import smbus
except (ImportError, RuntimeError):
    # TODO(will): Come up with a better hack for working on non-Raspberry Pi
    # systems.
    from testing.stub_smbus import StubSmbus
    smbus = StubSmbus()
import os
from tornado import ioloop
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient
from urllib.parse import urlencode

from brewery.brewhouse import Brewhouse
from git import Repo
from http_codes import HTTP_TIMEOUT
from joulia_webserver.client import JouliaHTTPClient
from joulia_webserver.client import JouliaWebsocketClient
from measurement.analog_reader import MCP3004AnalogReader
import settings
from update import UpdateManager


logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s %(asctime)s %(name)-12s %(message)s')
logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)

# Rate to check for updates. Set to 30 seconds.
UPDATE_CHECK_RATE = 30 * 1000  # milliseconds


def main():
    """Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance."""
    LOGGER.info('Starting brewery.')
    http_client = JouliaHTTPClient("http://" + settings.HOST,
                                   auth_token=settings.AUTHTOKEN)
    ws_address = "ws://{}/live/timeseries/socket/".format(settings.HOST)
    ws_client = JouliaWebsocketClient(ws_address, http_client,
                                      auth_token=settings.AUTHTOKEN)
    start_stop_client = AsyncHTTPClient()
    brewhouse_id = http_client.get_brewhouse_id()
    repo = Repo(os.getcwd())
    update_manager = UpdateManager(repo, http_client)
    system = System(http_client, ws_client, start_stop_client, brewhouse_id,
                    update_manager)
    system.watch_for_start()
    LOGGER.info("Brewery initialized.")

    ioloop.IOLoop.instance().start()


class System(object):
    def __init__(self, http_client, ws_client, start_stop_client, brewhouse_id,
                 update_manager):
        self.http_client = http_client
        self.ws_client = ws_client
        self.start_stop_client = start_stop_client
        self.brewhouse = None
        self.brewhouse_id = brewhouse_id
        self.update_manager = update_manager

        # Check for new versions periodically. Timers get turned on and off by
        # the recipe start/stop watchers.
        self.update_check_timer = ioloop.PeriodicCallback(
            self.update_manager.check_version, UPDATE_CHECK_RATE)

    def create_brewhouse(self, recipe_instance_pk):
        LOGGER.info("Creating brewhouse with recipe instance %s.",
                    recipe_instance_pk)
        analog_reader = create_analog_reader()
        gpio.setmode(gpio.BCM)

        recipe_instance = self.http_client.get_recipe_instance(
            recipe_instance_pk)
        recipe = self.http_client.get_recipe(recipe_instance.recipe_pk)

        with open("config.json", 'r') as configuration_file:
            configuration = json.load(configuration_file)

        brewhouse = Brewhouse.from_json(
            self.ws_client, gpio, analog_reader, recipe_instance_pk, recipe,
            configuration)

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
        uri = "http://{}/live/recipeInstance/start/".format(settings.HOST)
        self.start_stop_client.fetch(
            uri, handle_start_request, method="POST", body=urlencode(post_data),
            headers={'Authorization': 'Token {}'.format(settings.AUTHTOKEN)})

        # Check for updates while not running a brew session.
        self.update_check_timer.start()

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
                self.watch_for_start()

        LOGGER.info("Watching for recipe instance end on brewhouse %s.",
                    self.brewhouse_id)
        post_data = {'brewhouse': self.brewhouse_id}
        uri = "http://{}/live/recipeInstance/end/".format(settings.HOST)
        self.start_stop_client.fetch(
            uri, handle_end_request, method="POST", body=urlencode(post_data),
            headers={'Authorization': 'Token {}'.format(settings.AUTHTOKEN)})

    def end_brewing(self):
        self.brewhouse.cancel_timers()


def create_analog_reader():
    spi_port = 0
    spi_device = 0
    # Adafuit_GPIO.SPI.SpiDev will throw an ImportError when instantiating a new
    # instance, since they perform an import at runtime. Since this is the case,
    # we catch the import error when instantiating the spi bus here.
    try:
        from Adafruit_GPIO.SPI import SpiDev
        from Adafruit_MCP3008 import MCP3008
        spi = SpiDev(spi_port, spi_device)
    except (ImportError, FileNotFoundError):
        LOGGER.warning("Falling back to test analog reader.")
        from testing.stub_mcp3008 import StubSpiDev as SpiDev
        from testing.stub_mcp3008 import StubMCP3008 as MCP3008
        spi = SpiDev(spi_port, spi_device)
    mcp = MCP3008(spi=spi)
    analog_reference = 3.3  # Volts
    return MCP3004AnalogReader(mcp, analog_reference)


if __name__ == "__main__":
    main()  # pragma: no cover
