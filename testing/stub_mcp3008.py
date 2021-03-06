"""Stubs for Adafruit MCP3008 library.
"""

import logging


LOGGER = logging.getLogger(__name__)


class StubMCP3008(object):
    """Stubs MCP3008 from Adafruit_MCP3008 library.

    Does not inherit from the class directly since there are side-effects of it
    that cannot be mocked.
    """
    def __init__(self, spi):
        del spi
        self.counts = [0]*8

    def read_adc(self, channel):  # pylint: disable=missing-docstring
        assert channel < len(self.counts), \
            "Channel {} greater than {} available channels.".format(
                channel, len(self.counts))
        counts = self.counts[channel]
        LOGGER.debug("Getting stubbed mcp3008 counts %s at channel %s.",
                     counts, channel)
        return counts

    def set_counts(self, channel, counts):
        """Sets the counts to be returned for the requested channel."""
        LOGGER.debug("Setting stubbed mcp3008 counts to %s for channel %s.",
                     counts, channel)
        self.counts[channel] = counts


class StubSpiDev(object):
    """Stubs SpiDev from Adafruit_GPIO.SPI.

    Not actually useful at this point. Just used since a library
    Adafruit_GPIO.SPI.SpiDev depends on a linux only library. This just allows
    us to represent an empty object which would have been available from the
    Adafruit_GPIO library. The stub StubMCP3008, which consumes this stub, won't
    call this stub at all.
    """
    def __init__(self):
        pass
