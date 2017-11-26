"""Mock RTD sensor for faking measured temperature data."""

from measurement.rtd_sensor import RtdSensor


class StubRtdSensor(RtdSensor):
    """Fakes a measured temperature with a set temperature."""

    def __init__(self, temperature):  # pylint: disable=super-init-not-called
        self._temperature = temperature

        self.measure_calls = 0

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        self._temperature = value

    def measure(self):
        self.measure_calls += 1
        return self.temperature
