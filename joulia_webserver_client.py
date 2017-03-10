"""Client for interaction with Joulia Webserver. Should be used for all
communication with joulia-webserver, and offers an opportunity for subclassing
and stubbing the response from joulia-webserver.
"""

import datetime
import json
import pytz
import requests
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

import logging
LOGGER = logging.getLogger(__name__)


class JouliaWebserverClientBase(object):
    """Abstract class for clients connecting to Joulia Webserver.

    Attributes:
        address: Host address for API endpoints
        auth_token: Token that can be used for authenticating with the server
    """
    def __init__(self, address, auth_token=None):
        self.address = address
        self.auth_token = auth_token

    def identify(self, sensor_name, recipe_instance):
        raise NotImplementedError()


class JouliaHTTPClient(JouliaWebserverClientBase):
    """Client for interacting with Joulia Webserver REST endpoints and websocket
    endpoints.
    """
    _requests_service = requests

    def _authorization_headers(self):
        """Generates authorization headers for the instance."""
        if self.auth_token is not None:
            headers = {'Authorization': 'Token ' + self.auth_token}
        else:
            headers = {}
        return headers

    def _post(self, url, *args, **kwargs):
        """Helper function to help make posts to the server but add time
        between requests incase there are issues so we don't pile up a ton
        of requests. Attaches authentication based on instance.

        Args:
            url: Url to post to
            *args: To pass to `requests.post`
            **kwargs: To pass to `requests.post`
        """
        headers = self._authorization_headers()
        response = self._requests_service.post(url, headers=headers, *args,
                                               **kwargs)
        response.raise_for_status()
        return response

    @property
    def _identify_url(self):
        return self.address + "/live/timeseries/identify/"

    def identify(self, sensor_name, recipe_instance):
        """Sends a request to the server based on the current recipe instance
        to identify the sensors id number, given the `sensor_name`

        Args:
            sensor_name: The name of the sensor to identify.
            recipe_instance: The id number for the active recipe instance

        Returns: The id number for the sensor.
        """
        data = {'recipe_instance': recipe_instance, 'name': sensor_name}

        request = self._post(self._identify_url, data=data)
        identifier = request.json()['sensor']
        # self.ids[instance] =
        LOGGER.debug("Identified %s as %d", sensor_name, identifier)
        return identifier


class JouliaWebsocketClient(JouliaWebserverClientBase):
    """A Helper class for handling a synchronous connection to the websocket
    layer and establishing a queue system for messages when the websocket is
    not available.

    Attributes:
        http_client: JouliaHTTPClient instance for making required HTTP requests
            not supported by joulia-webserver yet.
        callbacks: A list of the registered callbacks for handling messages
            from the websocket.
        websocket: The tornado websocket client
    """
    _websocket_connect = websocket_connect

    def __init__(self, address, http_client, auth_token=None):
        super(JouliaWebsocketClient, self).__init__(address, auth_token)

        self.http_client = http_client

        self.callbacks = set()
        IOLoop.current().run_sync(lambda: self._connect(address))
        self._connect(address)

    @gen.coroutine
    def _connect(self, url):
        """Starts connection to the websocket streaming endpoint.

        Is a tornado coroutine, so the websocket connection is yielded,
        and we have a connection callback set.

        Args:
            url: URL to the websocket endpoint.
        """
        LOGGER.info("Establishing websocket connection at %s", url)
        self.websocket = yield self._websocket_connect(
            url, on_message_callback=self.on_message)
        LOGGER.info("Websocket connection established at %s", url)

    def write_message(self, message):
        """Serves as a ``write_message`` api to the websocket. Adds the new
        message to the queue, and calls the ``empty_queue`` method.

        Args:
            message: String-like message to send to the websocket
        """
        self.websocket.write_message(message)

    @staticmethod
    def clean_value(value):
        """Returns a cleaned value that will be appropriately interpreted.
        """
        if value is None:  # TODO: make server accept None
            return 0
        if value is True:
            return 1
        if value is False:
            return 0
        return value

    def update_sensor_value(self, recipe_instance, value, sensor):
        """Sends the current sensor value for the sensor to the server

        Args:
            recipe_instance: The recipe instance id to associate the measurement
                with
            value: The sampled value
            sensor: The sensor id for the equipment being sampled
        """
        LOGGER.debug("Sending data sample for sensor %s, recipe instance %s: "
                     "%g", sensor, recipe_instance, value)

        sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

        data = {'time': sample_time,
                'recipe_instance': recipe_instance,
                'value': self.clean_value(value),
                'sensor': sensor}
        self.websocket.write_message(json.dumps(data))

    def identify(self, sensor_name, recipe_instance):
        return self.http_client.identify(sensor_name, recipe_instance)

    def subscribe(self, recipe_instance, sensor):
        msg_string = json.dumps({'recipe_instance': recipe_instance,
                                 'sensor': sensor,
                                 'subscribe': True})
        self.websocket.write_message(msg_string)

    def register_callback(self, callback):
        """Registers a callback function to be called when a new message is
        received from the websocket.

        Args:
            callback: function to be called when a new message is received.
                The same arguments received by the standard
                ``on_message_callback`` callback for the websocket.
        """
        self.callbacks.add(callback)

    def on_message(self, message):
        """Callback called when the websocket receives new data.

        Calls all the registered callback functions with the message supplied.

        Arguments:
            message: the message received from the websocket peer.
        """
        if message is None:
            LOGGER.error('Websocket closed unexpectedly.')
            return

        for callback in self.callbacks:
            callback(message)
