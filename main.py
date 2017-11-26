"""Main code for launching a Brewhouse joulia-controller."""
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
import time
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient

from brewery.system import System
from git import Repo
from joulia_webserver.client import JouliaHTTPClient
from joulia_webserver.client import JouliaWebsocketClient
from measurement.analog_reader import MCP3004AnalogReader
import settings
from update import UpdateManager

logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)


def main():
    """Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance."""
    root_directory = os.path.dirname(os.path.realpath(__file__))
    LOGGER.info('Changing working directory to the directory of this file: %s',
                root_directory)
    os.chdir(root_directory)

    LOGGER.info('Starting brewery.')
    http_client = JouliaHTTPClient(settings.HTTP_PREFIX + "://" + settings.HOST,
                                   auth_token=settings.AUTHTOKEN)
    ws_address = "{}://{}/live/timeseries/socket/".format(
        settings.WS_PREFIX, settings.HOST)
    ws_client = JouliaWebsocketClient(ws_address, http_client,
                                      auth_token=settings.AUTHTOKEN)
    start_stop_client = AsyncHTTPClient()

    brewhouse_id = http_client.get_brewhouse_id()

    analog_reader = create_analog_reader()
    gpio.setmode(gpio.BCM)

    repo = Repo(os.getcwd())
    update_manager = UpdateManager(repo, http_client)
    system = System(http_client, ws_client, start_stop_client, brewhouse_id,
                    analog_reader, gpio, update_manager)
    system.watch_for_start()
    LOGGER.info("Brewery initialized.")

    ioloop.IOLoop.instance().start()


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
    # TODO(willjschmitt): This is a hack because networking is not up when this
    # is first called. We simply delay startup by 10seconds to allow networking
    # to come up.
    time.sleep(10.0)
    try:
        main()  # pragma: no cover
    except Exception as e:
        LOGGER.exception(e)
        raise e
