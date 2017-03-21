"""Main code for launching a Brewhouse joulia-controller."""
import logging.config
try:
    import RPi.GPIO as gpio
except (ImportError, RuntimeError):
    # TODO(will): Come up with a better hack for working on non-Raspberry Pi
    # systems.
    from testing.stub_gpio import StubGPIO
    gpio = StubGPIO()
try:
    import smbus
except (ImportError, RuntimeError):
    # TODO(will): Come up with a better hack for working on non-Raspberry Pi
    # systems.
    from testing.stub_smbus import StubSmbus
    smbus = StubSmbus()
import json
from tornado import ioloop
from tornado.escape import json_decode
from tornado.httpclient import AsyncHTTPClient

from brewery.brewhouse import Brewhouse
from brewery.pump import SimplePump
from brewery.vessels import HeatedVessel
from brewery.vessels import HeatExchangedVessel
from joulia_webserver_client import JouliaHTTPClient
from joulia_webserver_client import JouliaWebsocketClient
from measurement.arduino import AnalogReader
from measurement.gpio import OutputPin
from measurement.rtd_sensor import RtdSensor
import settings

logging.basicConfig(level=logging.INFO)
logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)


def main():
    """Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance."""
    LOGGER.info('Starting brewery.')
    address = "joulia.io"
    http_client = JouliaHTTPClient("http://" + address)
    ws_client = JouliaWebsocketClient("ws://" + address, http_client)
    start_stop_client = AsyncHTTPClient()
    system = System(ws_client, start_stop_client)
    system.watch_for_start()
    LOGGER.info("Brewery initialized.")

    ioloop.IOLoop.instance().start()


class System(object):
    def __init__(self, ws_client, start_stop_client):
        self.ws_client = ws_client
        self.start_stop_client = start_stop_client
        self.brewhouse = None

    def create_brewhouse(self, recipe_instance):
        analog_reader = create_analog_reader()
        gpio.setmode(gpio.BCM)

        boil_sensor_analog_pin = 0
        boil_sensor_rtd_alpha = 0.385
        boil_sensor_rtd_zero_resistance = 100.0
        boil_sensor_analog_reference = 3.3
        boil_sensor_vcc = 3.3
        boil_sensor_tau_filter = 10.0
        boil_sensor_rtd_top_resistance = 1.0E3
        boil_sensor_amplifier_resistor_a = 15.0E3
        boil_sensor_amplifier_resistor_b = 270.0E3
        boil_offset_resistance_bottom = 10.0E3
        boil_offset_resistance_top = 100.0E3
        boil_kettle_temperature_sensor = RtdSensor(
            analog_reader,
            boil_sensor_analog_pin, boil_sensor_rtd_alpha,
            boil_sensor_rtd_zero_resistance, boil_sensor_analog_reference,
            boil_sensor_vcc, boil_sensor_tau_filter,
            boil_sensor_rtd_top_resistance, boil_sensor_amplifier_resistor_a,
            boil_sensor_amplifier_resistor_b, boil_offset_resistance_bottom,
            boil_offset_resistance_top)

        boil_kettle_heating_element_rating = 5500.0
        boil_kettle_volume = 5.0
        boil_kettle_heating_pin_number = 0
        boil_kettle_heating_pin = OutputPin(
            gpio, boil_kettle_heating_pin_number)
        boil_kettle = HeatedVessel(
            self.ws_client, recipe_instance, boil_kettle_heating_element_rating,
            boil_kettle_volume, boil_kettle_temperature_sensor,
            boil_kettle_heating_pin)

        mash_sensor_analog_pin = 0
        mash_sensor_rtd_alpha = 0.385
        mash_sensor_rtd_zero_resistance = 100.0
        mash_sensor_analog_reference = 3.3
        mash_sensor_vcc = 3.3
        mash_sensor_tau_filter = 10.0
        mash_sensor_rtd_top_resistance = 1.0E3
        mash_sensor_amplifier_resistor_a = 15.0E3
        mash_sensor_amplifier_resistor_b = 270.0E3
        mash_offset_resistance_bottom = 10.0E3
        mash_offset_resistance_top = 100.0E3
        mash_tun_temperature_sensor = RtdSensor(
            analog_reader,
            mash_sensor_analog_pin, mash_sensor_rtd_alpha,
            mash_sensor_rtd_zero_resistance, mash_sensor_analog_reference,
            mash_sensor_vcc, mash_sensor_tau_filter,
            mash_sensor_rtd_top_resistance, mash_sensor_amplifier_resistor_a,
            mash_sensor_amplifier_resistor_b, mash_offset_resistance_bottom,
            mash_offset_resistance_top)

        mash_tun_volume = 5.0
        mash_temperature_profile = [(60.0, 155.0)]
        mash_tun = HeatExchangedVessel(
            self.ws_client, recipe_instance, mash_tun_volume,
            mash_tun_temperature_sensor,
            temperature_profile=mash_temperature_profile)

        pump_pin_number = 2
        pump_pin = OutputPin(gpio, pump_pin_number)
        main_pump = SimplePump(pump_pin)

        brewhouse = Brewhouse(self.ws_client, gpio, analog_reader, recipe_instance,
                              boil_kettle, mash_tun, main_pump)

        self.brewhouse = brewhouse

    def watch_for_start(self):
        """Makes a long-polling request to joulia-webserver to check
        if the server received a request to start a brewing session.

        Once the request completes, the internal method
        handle_start_request is executed.
        """

        def handle_start_request(response):
            """Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the startup
            logic for this Brewhouse
            """
            if response.error:
                LOGGER.error(response)
                self.watch_for_start()
            else:
                LOGGER.info("Got command to start brewing session.")
                response = json_decode(response.body)
                messages = response['messages']
                recipe_instance = messages['recipe_instance']
                self.create_brewhouse(recipe_instance)

        post_data = {'brewhouse': settings.BREWHOUSE_ID}
        uri = "http://joulia.io/live/recipeInstance/start/"
        self.start_stop_client.fetch(uri, handle_start_request, method="POST",
                                     body=json.dumps(post_data))

    def watch_for_end(self):
        """Makes a long-polling request to joulia-webserver to check
        if the server received a request to end the brewing session.

        Once the request completes, the internal method
        handle_end_request is executed.
        """

        def handle_end_request(response):
            """Handles the return from the long-poll request. If the
            request had an error (like timeout), it launches a new
            request. If the request succeeds, it fires the termination
            logic for this Brewhouse
            """
            if response.error:
                LOGGER.error(response)
                self.watch_for_end()
            else:
                LOGGER.info("Got command to end brewing session.")
                self.end_brewing()

        post_data = {'brewhouse': settings.BREWHOUSE_ID}
        uri = "http://joulia.io/live/recipeInstance/end/"
        self.start_stop_client.fetch(uri, handle_end_request, method="POST",
                                     body=json.dumps(post_data))

    def end_brewing(self):
        self.brewhouse.cancel_timers()


def create_analog_reader():
    i2c_bus = smbus.Bus(1)
    i2c_address = 0x0A
    return AnalogReader(i2c_bus, i2c_address)


if __name__ == "__main__":
    main()  # pragma: no cover
