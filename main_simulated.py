"""Main code for launching a simulated Brewhouse joulia-controller."""
import logging.config
import os

from tornado import ioloop

from brewery.system import SimulatedSystem
from measurement.analog_reader import MCP3004AnalogReader
import settings
from testing.stub_gpio import StubGPIO
from testing.stub_mcp3008 import StubSpiDev as StubSpiDev
from testing.stub_mcp3008 import StubMCP3008 as StubMCP3008

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

    analog_reader = create_analog_reader()
    gpio = StubGPIO()
    gpio.setmode(gpio.BCM)

    system = SimulatedSystem.create_from_settings(analog_reader, gpio)
    system.watch_for_start()
    system.run_simulation()
    LOGGER.info("Brewery initialized.")
    ioloop.IOLoop.instance().start()


def create_analog_reader():
    mcp = StubMCP3008(spi=StubSpiDev())
    analog_reference_volts = 3.3
    return MCP3004AnalogReader(mcp, analog_reference_volts)


if __name__ == "__main__":
    try:
        main()  # pragma: no cover
    except Exception as e:
        LOGGER.exception(e)
        raise e
