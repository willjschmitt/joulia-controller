"""Mock RTD sensor for faking measured temperature data."""


class StubRtdSensor(object):
    """Fakes a measured temperature with a set temperature."""

    def __init__(self, temperature):
        self.temperature = temperature

        self.measure_calls = 0

    def measure(self):
        self.measure_calls += 1
