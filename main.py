"""Main code for launching a Brewhouse joulia-controller."""
import logging.config
import RPi.GPIO as gpio
from tornado import ioloop

from brewery.brewhouse import Brewhouse
from brewery.vessels import HeatedVessel
from brewery.vessels import HeatExchangedVessel
from measurement.arduino import AnalogReader
from measurement.gpio import OutputPin
from measurement.rtd_sensor import RtdSensor
import settings

logging.basicConfig(level=logging.DEBUG)
logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)


def main():
    """Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance."""
    brewhouse = create_brewhouse()
    LOGGER.info('Brewery initialized.')

    ioloop.IOLoop.instance().start()


def create_brewhouse():
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
        client, recipe_instance, boil_kettle_heating_element_rating,
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
        client, recipe_instance, mash_tun_volume,
        mash_tun_temperature_sensor,
        temperature_profile=mash_temperature_profile)

    pump_pin_number = 2
    pump_pin = OutputPin(gpio, pump_pin_number)
    main_pump = SimplePump(pump_pin)

    brewhouse = Brewhouse(ws_client, gpio, analog_reader, recipe_instance,
                          boil_kettle, mash_tun, main_pump)

    return brewhouse


def create_analog_reader():
    i2c_bus = smbus.Bus(1)
    i2c_address = 0x0A
    return AnalogReader(i2c_bus, i2c_address)


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
            logging.error(response)
            self.watch_for_start()
        else:
            LOGGER.info("Got command to start")
            response = json_decode(response.body)
            messages = response['messages']
            self.recipe_instance = messages['recipe_instance']
            self.start_brewing()
            self.watch_for_end()

    http_client = AsyncHTTPClient()
    post_data = {'brewhouse': settings.BREWHOUSE_ID}
    uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/start/"
    headers = {'Authorization': 'Token ' + self.authtoken}
    http_client.fetch(uri, handle_start_request,
                      headers=headers,
                      method="POST",
                      body=urllib.urlencode(post_data))


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
            self.watch_for_end()
        else:
            self.end_brewing()

    http_client = AsyncHTTPClient()
    post_data = {'brewhouse': settings.BREWHOUSE_ID}
    uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/end/"
    headers = {'Authorization': 'Token ' + self.authtoken}
    http_client.fetch(uri, handle_end_request,
                      headers=headers,
                      method="POST",
                      body=urllib.urlencode(post_data))

if __name__ == "__main__":
    main()
