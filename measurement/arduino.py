"""Utility functions for interacting with arduino over I2C"""

from utils import GPIO_MOCK_API_ACTIVE

if not GPIO_MOCK_API_ACTIVE:
    import smbus

def analog_read(channel):
    """Reads the counts value broadcast from an arduino at the indicated
    channel.

    Args:
        channel: The analog pin to read at.
    """
    bus = smbus.SMBus(1)
    address = 0x0A

    bus.write_byte(address, channel)

    counts1 = bus.read_byte_data(address, 0)
    counts2 = bus.read_byte_data(address, 1)
    counts = (counts1 << 8) + counts2
    return counts