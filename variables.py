import datetime
import json
import logging
import pytz
import requests
from tornado import ioloop
from weakref import WeakKeyDictionary
from _weakrefset import WeakSet

from joulia_webserver_client import JouliaWebsocketClient
import settings
from utils import rgetattr
from utils import exists_and_not_none


LOGGER = logging.getLogger(__name__)


class ManagedVariable(object):
    """Top level class to represent a managed variable that controls how
    the property is get or set for a given object.

    Meant to be an abstract class to help with binding variables with
    joulia-webserver.

    Attributes:
        default: Value to use for get's before any other process has set it
        sensor_name: The name of the sensor to use for handshakes with the
            server.
        clients: A dictionary that maps an object to it's instances client for
            communicating with the server.
        data: A dictionary that maps an object to its instance's value. This
            is necessary, because this variable needs to be assigned at the
            class level in order for get/set to work correctly.
        ids: A dictionary that maps an object to its identifier on the server.
        authtokens: A dictionary that maps an object to its instance's
            authorization token.
        callbacks: A callback to be called when a related frame is received
            from the server.
        registered: A set of the instances of the class containing the instance
            of the ManagedVariable that have registered.
        registered: A set of the instances of the class containing the instance
            of the ManagedVariable that have subscribed.
    """

    def __init__(self, sensor_name, default=None):
        self.default = default
        self.sensor_name = sensor_name

        self.clients = WeakKeyDictionary()
        self.recipe_instances = WeakKeyDictionary()
        self.data = WeakKeyDictionary()
        self.ids = WeakKeyDictionary()
        self.authtokens = WeakKeyDictionary()
        self.callbacks = WeakKeyDictionary()
        self.registered = WeakSet()

        # External APIs exposed for mocking and replacing
        self._requests_service = requests

    def __get__(self, obj, obj_type):
        """Retrieves the current value for the object requested"""
        # Allows us to be able to access the property directly to get
        # at its methods like register, subscribe, etc.
        if obj is None:
            return self

        # Set the value to the default if it doesn't have a value yet
        if obj not in self.data and self.default is not None:
            self.data[obj] = self.default
        elif obj not in self.data and self.default is None:
            raise AttributeError("Variable {} attempted to be accessed on {}"
                                 " prior to initialization and no default was"
                                 " set.".format(self.sensor_name, obj))

        return self.data.get(obj)

    def __set__(self, obj, value):
        """Sets the current value for the object requested"""
        self.data[obj] = value

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        """Registers this instance with the appropriate authentication.
        Indicates this ManagedVariable is ready to participate in interactions
        with the server. Subclasses will dictate the behavior of registered
        instances.

        Args:
            client: The http/ws client to pass requests through.
            instance: The instance to subscribe.
            recipe_instance: The recipe_instance id from the server for the
                current recipe execution.
            authtoken: The authentication token to authenticate with API
            callback: Function that should be called when an update is
                retrieved. Useful if additional action should be taken
                to validate the servers's feedback.
        """
        self.clients[instance] = client
        self.authtokens[instance] = authtoken
        self.callbacks[instance] = callback

        self.identify(instance, recipe_instance)

        self.registered.add(instance)

    def identify(self, instance, recipe_instance):
        """Requests the sensor id from the server for the current instance of
        the variable and stores it for future use.

        Arguments:
            instance: the instance the variable is associated with.
            recipe_instance: the recipe identifier for the session of brewing.
        """
        client = self.clients[instance]
        id_sensor = client.identify(instance, recipe_instance)
        self.ids[instance] = id_sensor


class WebsocketVariable(ManagedVariable):
    """A variable that has a websocket connection established for it.

    Attributes:
        websocket: A class-level websocket connection with the server used
            for exchanging data to/from the server.
    """

    def __init__(self, *args, **kwargs):
        super(WebsocketVariable, self).__init__(*args, **kwargs)
        self.callback = WeakKeyDictionary()

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        assert isinstance(client, JouliaWebsocketClient)

        super(WebsocketVariable, self).register(
            client, instance, recipe_instance, authtoken=authtoken,
            callback=callback)


class StreamingVariable(WebsocketVariable):
    """A version of `ManagedVaraiable` that publishes to a sensor stream
    on the server.
    """

    def __set__(self, instance, value):
        """Sets the value to the current instance and sends the new value
        to the server.

        Args:
            instance: The instance to set the value for
            value: The value to set
        """
        super(StreamingVariable, self).__set__(instance, value)
        client = self.clients[instance]
        recipe_instance = self.recipe_instances[instance]
        sensor = self.ids[instance]
        client.update_sensor_value(recipe_instance, value, sensor)

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        super(StreamingVariable, self).register(
            client, instance, recipe_instance, authtoken=authtoken,
            callback=callback)
        self.recipe_instances[instance] = recipe_instance
        self.identify(instance, recipe_instance)


class SubscribableVariable(WebsocketVariable):
    """A version of `ManagedVariable` that subscribes to a sensor stream
    on the server, and uses the values received to set the property.
    """

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        super(SubscribableVariable, self).register(
            client, instance, recipe_instance, authtoken=authtoken,
            callback=callback)
        client.register_callback(self.__class__.on_message)
        self._subscribe(instance, self.sensor_name, recipe_instance)

    def _subscribe(self, instance, sensor_name, recipe_instance,
                   variable_type="value"):
        """Creates a subscription given a sensor name and recipe instance

        This is separated mostly for functions that want to create many
        sensors from one, like for an ``OverridableVariable``.

        Args:
            instance: The instance that is subscribing to the stream
            sensor_name: The string name for the variable to send a
                subscription request to the server
            recipe_instance: The id for the recipe instance the subscription
                is for
            variable_type: Indicates if the stream is for a "value" or
                "override". Other reasonable values might be made available
                later. Defaults to "value".
        """

        # If we don't have a subscription setup yet, send a subscribe
        # request through the websocket
        if (sensor_name, recipe_instance,) not in self.subscribers:
            LOGGER.info('Subscribing to %s, instance %s',
                        self.sensor_name, recipe_instance)

            sensor = self.ids[instance]
            subscriber = {'descriptor': self,
                          'instance': instance,
                          'var_type': variable_type}
            self.subscribers[(sensor, recipe_instance)] = subscriber

            client = self.clients[instance]
            client.subscribe(recipe_instance, sensor)

    @classmethod
    def on_message(cls, response):
        """A generic callback to handle the response from a websocket
        communication back, which will receive the data and set it

        Args:
            response: The websocket response
        """
        response_data = json.loads(response)
        sensor = response_data['sensor']
        recipe_instance = response_data['recipe_instance']
        subscriber_key = (sensor, recipe_instance)
        subscriber = cls.subscribers[subscriber_key]

        response_value = response_data['value']

        descriptor = subscriber['descriptor']
        instance = subscriber['instance']

        if subscriber['var_type'] == 'value':
            current_value = descriptor.data[instance]
            current_type = type(current_value)
            descriptor.data[instance] = current_type(response_value)
            if exists_and_not_none(descriptor.callback, instance):
                callback = descriptor.callback[instance]
                callback(response_value)
        elif subscriber['var_type'] == 'override':
            descriptor.overridden[instance] = bool(response_value)

    subscribers = {}


class OverridableVariable(StreamingVariable, SubscribableVariable):
    """A variable that is bi-directional. That is, it can be overridden
    by the user interface, but the override can be released for the controls
    to control
    """
    def __init__(self, sensor_name, default=None):
        StreamingVariable.__init__(self, sensor_name, default=default)
        SubscribableVariable.__init__(self, sensor_name, default=default)

        super(OverridableVariable, self).__init__(sensor_name)
        self.overridden = WeakKeyDictionary()

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        """Subscribes to the feed for the variable as well as the
        complementing override.
        """
        super(OverridableVariable, self).register(instance, recipe_instance,
                                                  authtoken=authtoken)

        self.overridden[instance] = False
        super(OverridableVariable, self).register(instance, recipe_instance,
                                                  callback=callback)

        self._subscribe(instance, self.sensor_name + "Override",
                        recipe_instance, 'override')

        self.register(instance, recipe_instance)

    def __set__(self, obj, value):
        """override the __set__ function to check if an override is not in
        place on the variable before allowing to go to the normal __set__
        """
        # See if the controls are allowed to set this value at the moment.
        if self.overridden.get(obj):
            return

        super(OverridableVariable, self).__set__(obj, value)
        client = self.clients[obj]
        client.update_sensor_value(obj)


class DataStreamer(object):
    """A streaming class to stream data periodically. Has an internal
    clock to send data at the frequency found in
    ``settings.DATASTREAM_FREQUENCY``
    """
    time_out_wait = 10

    data_post_service = (settings.HTTP_PREFIX + ":" + settings.HOST
                         + "/live/timeseries/new/")
    data_identify_service = (settings.HTTP_PREFIX + ":" + settings.HOST
                             + "/live/timeseries/identify/")

    def __init__(self, streaming_class, recipe_instance):
        self.streaming_class = streaming_class
        self.recipe_instance = recipe_instance

        self.sensor_map = {}
        self.time_out_counter = 0

        callback = ioloop.PeriodicCallback(self.post_data,
                                           settings.DATASTREAM_FREQUENCY)
        callback.start()

    def register(self, attr, name=None):
        """Registers variable with server

        Args:
            attr: Name of the attribute to register with the server
            name: Name to register the variable as with the server. Defaults
                to ``attr`` if not provided.
        """
        if name is None:  # Default to attribute as the name
            name = attr
        if name in self.sensor_map:
            # This makes sure we aren't overwriting anything
            raise AttributeError('{} already exists in streaming service.'
                                 ''.format(name))
        # Map the attribute to the server var name
        self.sensor_map[name] = {'attr':attr}

    def post_data(self):
        """Posts the current values of the data to the server"""
        if self.time_out_counter > 0:
            self.time_out_counter -= 1
        else:
            LOGGER.debug('Data streamer %r sending data.',self)

            # Post temperature updates to server
            sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

            for sensor_name, sensor in self.sensor_map.iteritems():
                try:
                    self.post_sensor_data(sensor_name, sensor, sample_time)
                except requests.exceptions.RequestException:
                    LOGGER.error("Failed to post sensor %s. Will retry later.",
                                 sensor_name)
                    continue

    def post_sensor_data(self, sensor_name, sensor, sample_time):
        # Get the sensor ID if we don't have it already
        if 'id' not in sensor:
            self.get_sensor_id(sensor_name, sensor)

        # Send the data
        try:
            value = rgetattr(self.streaming_class, sensor['attr'])
            if value is None:  # TODO: make server accept None
                value = "0"
            if value is True:
                value = 'true'
            if value is False:
                value = 'false'
            data = {'time': sample_time,
                    'recipe_instance': self.recipe_instance,
                    'value': value,
                    'sensor': sensor['id']}
            # TODO: add authorization
            # if self.authtokens[instance] is not None:
            #     headers = {
            #         'Authorization': 'Token ' + self.authtokens[instance]
            #     }
            # else:
            #     headers = {}
            headers = {}
            request = requests.post(self.data_post_service,
                                    data=data, headers=headers)
        except requests.exceptions.ConnectionError as e:
            LOGGER.info("Server not there. Will retry later.")
            self.time_out_counter = self.time_out_wait
            raise e

        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOGGER.info("Server returned error status. Will retry later. (%s)",
                        request.text)
            self.time_out_counter = self.time_out_wait
            raise e

        return

    def get_sensor_id(self, sensor_name, sensor):
        try:
            data = {'recipe_instance': self.recipe_instance,
                    'name': sensor_name}
            # TODO: add authorization
            # if self.authtokens[instance] is not None:
            #     headers = {
            #         'Authorization': 'Token ' + self.authtokens[instance]
            #     }
            # else:
            #     headers = {}
            headers = {}

            request = requests.post(self.data_identify_service,
                                    data=data, headers=headers)
        except requests.exceptions.ConnectionError as e:
            LOGGER.error("Server not there. Will retry later.")
            self.time_out_counter = self.time_out_wait
            raise e

        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOGGER.error("Server returned error status. Will retry later. (%s)",
                         request.text)
            self.time_out_counter = self.time_out_wait
            raise e

        sensor['id'] = request.json()['sensor']