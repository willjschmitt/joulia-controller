"""Utility functions for interacting with arduino over I2C"""

import smbus
import time

bus = smbus.SMBus(1)
address = 0x0A


def analog_read(channel):
    """Reads the counts value broadcast from an arduino at the indicated
    channel.

    Args:
        channel: The analog pin to read at.
    """
    bus.write_byte(address, channel)
    time.sleep(0.005)
    counts1 = bus.read_byte(address) & 0xFF
    time.sleep(0.005)
    counts2 = bus.read_byte(address) & 0xFF
    counts = counts1 + (counts2 << 8)
    return counts
