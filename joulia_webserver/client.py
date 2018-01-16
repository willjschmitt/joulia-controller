"""Client for interaction with Joulia Webserver. Should be used for all
communication with joulia-webserver, and offers an opportunity for subclassing
and stubbing the response from joulia-webserver.
"""

from collections import namedtuple
import datetime
import json
import logging

from joulia_webserver.models import MashStep
from joulia_webserver.models import MashProfile
from joulia_webserver.models import Recipe
from joulia_webserver.models import RecipeInstance
import pytz
import requests
from tornado import gen
from tornado.httpclient import HTTPRequest
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

LOGGER = logging.getLogger(__name__)


VALUE_VARIABLE_TYPE = 'value'
OVERRIDE_VARIABLE_TYPE = 'override'


class JouliaWebserverClientBase(object):
    """Abstract class for clients connecting to Joulia Webserver.

    Attributes:
        address: Host address for API endpoints
        auth_token: Token that can be used for authenticating with the server
    """
    def __init__(self, address, auth_token=None):
        self.address = address
        self.auth_token = auth_token

    def identify(self, sensor_name, recipe_instance, variable_type):
        """Sends a request to the server based on the current recipe instance
        to identify the sensors id number, given the `sensor_name`

        Args:
            sensor_name: The name of the sensor to identify.
            recipe_instance: The id number for the active recipe instance
            variable_type: The type of variable to identify (e.g. 'value' vs
                'override').

        Returns: A tuple with the id number and variable_type for the sensor.
        """
        raise NotImplementedError()

    def update_sensor_value(self, recipe_instance, value, sensor):
        """Sends the current sensor value for the sensor to the server

        Args:
            recipe_instance: The recipe instance id to associate the measurement
                with
            value: The sampled value
            sensor: The sensor id for the equipment being sampled
        """
        raise NotImplementedError()

    @staticmethod
    def clean_value(value):
        """Returns a cleaned value that will be appropriately interpreted."""
        if value is None:  # TODO: make server accept None
            return 0
        if value is True:
            return 1
        if value is False:
            return 0
        return value

    def _authorization_headers(self):
        """Generates authorization headers for the instance."""
        if self.auth_token is not None:
            headers = {'Authorization': 'Token ' + self.auth_token}
        else:
            headers = {}
        return headers


class JouliaHTTPClient(JouliaWebserverClientBase):
    """Client for interacting with Joulia Webserver REST endpoints and websocket
    endpoints.
    """
    _requests_service = requests

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

    def _get(self, url, *args, **kwargs):
        """Helper function to help make get requests to the server.

        Args:
            url: Url to post to
            *args: To pass to `requests.post`
            **kwargs: To pass to `requests.post`
        """
        headers = self._authorization_headers()
        response = self._requests_service.get(url, headers=headers, *args,
                                              **kwargs)
        response.raise_for_status()
        return response

    @property
    def _get_brewhouse_id_url(self):
        return self.address + "/brewery/api/brewhouse_from_token/"

    def get_brewhouse_id(self):
        """Requests server for the brewhouse ID associated with this client via
        the Token used for authenticating it.
        """
        response = self._get(self._get_brewhouse_id_url)
        brewhouse = response.json()['brewhouse']
        LOGGER.debug("Brewhouse identified as %d", brewhouse)
        return brewhouse

    @property
    def _identify_url(self):
        return self.address + "/live/timeseries/identify/"

    def identify(self, sensor_name, recipe_instance, variable_type):
        data = {
            'recipe_instance': recipe_instance,
            'name': sensor_name,
            'variable_type': variable_type,
        }

        response = self._post(self._identify_url, data=data)
        deserialized_response = response.json()
        identifier = deserialized_response['sensor']
        LOGGER.debug("Identified %s as %d", sensor_name, identifier)
        return identifier

    @property
    def _update_sensor_value_url(self):
        return self.address + "/live/timeseries/new/"

    def update_sensor_value(self, recipe_instance, value, sensor):
        sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

        data = {'time': sample_time,
                'recipe_instance': recipe_instance,
                'value': self.clean_value(value),
                'sensor': sensor}
        self._post(self._update_sensor_value_url, data=data)

    def _get_mash_points_url(self, recipe_pk):
        return "{}/brewery/api/mash_point/?recipe={}".format(self.address,
                                                             recipe_pk)

    def get_mash_points(self, recipe_pk):
        """Retrieves the mash points associated with a recipe instance, which
        define the mash profile.

        Args:
            recipe_pk: the id for the recipe interested in for the mash profile.

        Returns:
            Mash points as an array of (duration, temperature) pairs.
        """
        mash_points_response = self._get(self._get_mash_points_url(recipe_pk))
        mash_points = mash_points_response.json()
        return [MashStep(pt["time"], pt["temperature"]) for pt in mash_points]

    def _get_recipe_instance_url(self, recipe_instance_pk):
        return "{}/brewery/api/recipeInstance/{}/".format(
            self.address, recipe_instance_pk)

    def get_recipe_instance(self, recipe_instance_pk):
        url = self._get_recipe_instance_url(recipe_instance_pk)
        response = self._get(url)
        json_response = response.json()
        return RecipeInstance.from_joulia_webserver_response(json_response)

    def _get_recipe_url(self, recipe_pk):
        return "{}/brewery/api/recipe/{}/".format(self.address, recipe_pk)

    def get_recipe(self, recipe_pk):
        """Retrieves the recipe associated with a recipe instance and loads it
        into a Recipe object.

        Args:
            recipe_pk: the primary key/id for the recipe interested in for the
                mash profile.

        Returns:
            Mash points as an array of (duration, temperature) pairs.
        """
        mash_points = self.get_mash_points(recipe_pk)
        mash_profile = MashProfile(mash_points)

        recipe_url = self._get_recipe_url(recipe_pk)
        recipe_response = self._get(recipe_url)
        recipe_json_response = recipe_response.json()

        return Recipe.from_joulia_webserver(recipe_json_response, mash_profile)

    @property
    def _get_joulia_controller_release_url(self):
        return "{}/brewery/api/joulia_controller_release/".format(self.address)

    def get_latest_joulia_controller_release(self):
        """Gets the latest Joulia Controller Release. Queries for all of them,
        then selects the last one. If there are no releases, returns a dict with
        "commit_hash" populated as None."""
        response = self._get(self._get_joulia_controller_release_url)
        json_response = response.json()
        if len(json_response) == 0:
            return {"commit_hash": None}
        return json_response[-1]

    def _get_brewhouse_url(self, brewhouse_pk):
        return "{}/brewery/api/brewhouse/{}/".format(self.address, brewhouse_pk)

    def get_brewhouse(self, brewhouse_pk):
        """Gets the Brewhouse, which includes configuration information from the
        Joulia Webserver. Returned data is in json form.

        Args:
            brewhouse_pk: The primary key for the Brewhouse to query.
        """
        brewhouse_url = self._get_brewhouse_url(brewhouse_pk)
        response = self._get(brewhouse_url)
        return response.json()

    def update_brewhouse(self, brewhouse):
        """Gets the Brewhouse, which includes configuration information from the
        Joulia Webserver. Returned data is in json form.

        Args:
            brewhouse: The data to update the brewhouse with. Must have at least
                'id' set on it.
        """
        brewhouse_url = self._get_brewhouse_url(brewhouse['id'])
        response = self._post(brewhouse_url, data=brewhouse)
        return response.json()

    def save_brewhouse_software_version(self, brewhouse_pk, software_pk):
        """Updates the software version for the brewhouse.

        Should be used to tell the server the software has been updated to a
        specific version.

        Will get the brewhouse using get_brewhouse then update with
        update_brewhouse.

        Args:
            brewhouse_pk: The brewhouse id to update.
            software_pk: The software release version updated to.
        """
        brewhouse = self.get_brewhouse(brewhouse_pk)
        brewhouse['software_version'] = software_pk
        _ = self.update_brewhouse(brewhouse)


class JouliaWebsocketClient(JouliaWebserverClientBase):
    """A Helper class for handling a synchronous connection to the websocket
    layer and establishing a queue system for messages when the websocket is
    not available.

    Attributes:
        address: The address used to connect to the websocket server.
        http_client: JouliaHTTPClient instance for making required HTTP requests
            not supported by joulia-webserver yet.
        callbacks: A list of the registered callbacks for handling messages
            from the websocket.
        websocket: The tornado websocket client
    """

    # Represents a simple subscription made to the server for a particular
    # sensor in a recipe_instance.
    Subscription = namedtuple('Subscription', ('recipe_instance', 'sensor',))

    def __init__(self, address, http_client, auth_token=None):
        super(JouliaWebsocketClient, self).__init__(address, auth_token)

        self.address = address
        self.http_client = http_client

        self.callbacks = set()

        self._subscriptions = set()

        IOLoop.current().run_sync(self._connect)

    @gen.coroutine
    def _connect(self):
        """Starts connection to the websocket streaming endpoint.

        Is a tornado coroutine, so the websocket connection is yielded,
        and we have a connection callback set.
        """
        LOGGER.info("Establishing websocket connection at %s", self.address)
        http_request = HTTPRequest(
            self.address, headers=self._authorization_headers())
        self.websocket = yield self._websocket_connect(
            http_request, on_message_callback=self.on_message)
        LOGGER.info("Websocket connection established at %s", self.address)

    def _reconnect(self):
        """After a connection is dropped, reconnect to the websocket.

        Re-subscribes to any subscriptions made through ``subscribe``.
        """
        # TODO(willjschmitt): Add re-connect backoff if reconnecting fails
        # continuously.
        LOGGER.info("Reconnecting to websocket and re-subscribing.")
        IOLoop.current().run_sync(self._connect)
        for subscription in self._subscriptions:
            self.subscribe(subscription.recipe_instance, subscription.sensor)

    @gen.coroutine
    def _websocket_connect(self, url, on_message_callback=None):
        websocket = yield websocket_connect(
            url, on_message_callback=on_message_callback)
        return websocket

    def write_message(self, message):
        """Serves as a ``write_message`` api to the websocket. Adds the new
        message to the queue, and calls the ``empty_queue`` method.

        Args:
            message: String-like message to send to the websocket
        """
        self.websocket.write_message(message)

    def update_sensor_value(self, recipe_instance, value, sensor):
        clean_value = self.clean_value(value)
        LOGGER.debug("Sending data sample for sensor %s, recipe instance %s: "
                     "%g (raw: %s)", sensor, recipe_instance, clean_value,
                     value)

        sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

        data = {'time': sample_time,
                'recipe_instance': recipe_instance,
                'value': clean_value,
                'sensor': sensor}
        self.websocket.write_message(json.dumps(data))

    def identify(self, sensor_name, recipe_instance, variable_type):
        return self.http_client.identify(
            sensor_name, recipe_instance, variable_type)

    def subscribe(self, recipe_instance, sensor):
        LOGGER.info("Subscribing to sensor %s, recipe instance %s.", sensor,
                    recipe_instance)
        self._subscriptions.add(self.Subscription(
            recipe_instance=recipe_instance, sensor=sensor))
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
            self._reconnect()
            return

        for callback in self.callbacks:
            callback(message)
