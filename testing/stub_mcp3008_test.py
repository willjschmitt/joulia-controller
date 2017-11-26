"""Tests for the testing.stub_mcp3008 module."""

import unittest

from testing.stub_mcp3008 import StubMCP3008
from testing.stub_mcp3008 import StubSpiDev


class TestStubMCP3008(unittest.TestCase):
    """Tests for the StubMCP3008 class."""

    def test_read_adc(self):
        mcp = StubMCP3008(StubSpiDev())
        for chan in range(8):
            mcp.counts[chan] = chan
            self.assertEqual(mcp.read_adc(chan), chan)
