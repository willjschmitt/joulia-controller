"""Stub for mocking up the smbus library on non-Raspberry Pi's."""

class StubSmbus(object):
    """Mocks the smbus library on ubuntu/raspberry pi systems."""

    @staticmethod
    def Bus(bus_number):  # pylint: disable=invalid-name
        """Creates a mocked version (None) of the smbus.Bus class."""
        del bus_number
        return None
