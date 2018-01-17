"""Main code for launching a Brewhouse joulia-controller."""
import logging.config
import os
import time

from Adafruit_GPIO.SPI import SpiDev
from Adafruit_MCP3008 import MCP3008
import RPi.GPIO as gpio
from tornado import ioloop

from brewery.system import System
from measurement.analog_reader import MCP3004AnalogReader
import settings

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
    gpio.setmode(gpio.BCM)

    system = System.create_from_settings(analog_reader, gpio)
    system.watch_for_start()
    ioloop.IOLoop.instance().start()


def create_analog_reader():
    spi_port = 0
    spi_device = 0
    spi = SpiDev(spi_port, spi_device)
    mcp = MCP3008(spi=spi)
    analog_reference_volts = 3.3
    return MCP3004AnalogReader(mcp, analog_reference_volts)


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
