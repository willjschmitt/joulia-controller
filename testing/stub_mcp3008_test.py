"""Tests for the testing.stub_mcp3008 module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest

from testing.stub_mcp3008 import StubMCP3008
from testing.stub_mcp3008 import StubSpiDev


class TestStubMCP3008(unittest.TestCase):
    """Tests for the StubMCP3008 class."""

    def setUp(self):
        self.mcp = StubMCP3008(StubSpiDev())

    def test_read_adc(self):
        for chan in range(8):
            self.mcp.counts[chan] = chan
            self.assertEqual(self.mcp.read_adc(chan), chan)

    def test_set_counts(self):
        channel = 4
        counts = 1024
        self.mcp.set_counts(channel, counts)
        self.assertEqual(self.mcp.read_adc(channel), counts)
