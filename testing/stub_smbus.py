"""Stub for mocking up the smbus library on non-Raspberry Pi's."""

class StubSmbus(object):
    """Mocks the smbus library on ubuntu/raspberry pi systems."""

    def Bus(self, bus_number):
        return None