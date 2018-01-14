import json
import logging
from weakref import WeakKeyDictionary
from weakref import WeakSet

import requests
from tornado import ioloop

from joulia_webserver.client import JouliaWebsocketClient
from utils import exists_and_not_none
from utils import rgetattr

LOGGER = logging.getLogger(__name__)


VALUE_VARIABLE_TYPE = 'value'
OVERRIDE_VARIABLE_TYPE = 'override'


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
        variable_types: A dictionary mapping a sensor id to the variable type.
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
        self.ids = {}
        self.variable_types = {}
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
        if obj not in self.data:
            if self.default is None:
                raise AttributeError(
                    "Variable {} attempted to be accessed on {} prior to"
                    " initialization and no default was set."
                    "".format(self.sensor_name, obj))
            self.data[obj] = self.default

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

        self.recipe_instances[instance] = recipe_instance
        self.authtokens[instance] = authtoken
        self.callbacks[instance] = callback

        self.identify(instance, recipe_instance)

        self.registered.add(instance)

    def identify(self, instance, recipe_instance,
                 variable_type=VALUE_VARIABLE_TYPE):
        """Requests the sensor id from the server for the current instance of
        the variable and stores it for future use.

        Arguments:
            instance: the instance the variable is associated with.
            recipe_instance: the recipe identifier for the session of brewing.
            variable_type: The type of variable to subscribe to (e.g. 'value' or
                'override'). Defaults to 'value'.
        """
        client = self.clients[instance]
        id_sensor = client.identify(
            self.sensor_name, recipe_instance, variable_type)
        LOGGER.info("Identified sensor %s in recipe_instance %s as id %s.",
                    self.sensor_name, recipe_instance, id_sensor)
        self.ids[(instance, variable_type)] = id_sensor
        self.variable_types[id_sensor] = variable_type


class WebsocketVariable(ManagedVariable):
    """A variable that has a websocket connection established for it.

    Attributes:
        websocket: A class-level websocket connection with the server used
            for exchanging data to/from the server.
    """

    def __init__(self, sensor_name, default=None):
        super(WebsocketVariable, self).__init__(sensor_name, default=default)
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
        sensor = self.ids[(instance, VALUE_VARIABLE_TYPE)]
        LOGGER.debug("Sending new value for %s: %s.", self.sensor_name, value)
        client.update_sensor_value(recipe_instance, value, sensor)


class SubscribableVariable(WebsocketVariable):
    """A version of `ManagedVariable` that subscribes to a sensor stream
    on the server, and uses the values received to set the property.
    """

    def __init__(self, sensor_name, default=None):
        super(SubscribableVariable, self).__init__(sensor_name, default=default)
        self.subscribers = {}

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        super(SubscribableVariable, self).register(
            client, instance, recipe_instance, authtoken=authtoken,
            callback=callback)
        client.register_callback(self.on_message)
        self._subscribe(instance, recipe_instance)

    def _subscribe(self, instance, recipe_instance,
                   variable_type=VALUE_VARIABLE_TYPE):
        """Creates a subscription given a sensor name and recipe instance

        Args:
            instance: The instance that is subscribing to the stream
            recipe_instance: The id for the recipe instance the subscription
                is for
            variable_type: Indicates if the stream is for a "value" or
                "override". Other reasonable values might be made available
                later. Defaults to "value".
        """
        # If we don't have a subscription setup yet, send a subscribe
        # request through the websocket
        sensor_key = (instance, variable_type)
        if sensor_key not in self.ids:
            self.identify(instance, recipe_instance, variable_type)
        sensor = self.ids[sensor_key]
        subscription_key = (sensor, variable_type, recipe_instance)
        if subscription_key not in self.subscribers:
            LOGGER.info('Subscribing to %s (%s:%s), instance %s',
                        sensor, self.sensor_name, variable_type,
                        recipe_instance)

            subscriber = {'instance': instance}
            self.subscribers[subscription_key] = subscriber

            client = self.clients[instance]
            client.subscribe(recipe_instance, sensor)

    def on_message(self, response):
        """A generic callback to handle the response from a websocket
        communication back, which will receive the data and set it

        Args:
            response: The websocket response
        """
        response_data = json.loads(response)
        sensor = response_data['sensor']
        variable_type = response_data.get('variable_type', "value")
        recipe_instance = response_data['recipe_instance']
        subscriber_key = (sensor, variable_type, recipe_instance)

        # TODO(willjschmitt): Handle subscribers in client.
        if subscriber_key not in self.subscribers:
            return

        response_value = response_data['value']

        LOGGER.debug("Received updated value %s for sensor %s(%s),"
                     " variable_type %s, recipe_instance %s.", response_value,
                     sensor, self.sensor_name, variable_type, recipe_instance)

        subscriber = self.subscribers[subscriber_key]

        instance = subscriber['instance']

        if variable_type == 'value':
            # Attempts to convert data to the variable type of currently stored
            # data if it exists. Otherwise, just sets it to the default parsed
            # type from the json object.
            if instance in self.data:
                current_value = self.data[instance]
                current_type = type(current_value)
                self.data[instance] = current_type(response_value)
            else:
                self.data[instance] = response_value

            if exists_and_not_none(self.callbacks, instance):
                callback = self.callbacks[instance]
                callback(response_value)


class BidirectionalVariable(StreamingVariable, SubscribableVariable):
    """A variable that is bi-directional, but has no override logic. Only can
    stream data in a two-way manner regardless of who made the update.
    """
    pass


class OverridableVariable(StreamingVariable, SubscribableVariable):
    """A variable that is bi-directional. That is, it can be overridden
    by the user interface, but the override can be released for the controls
    to control
    """
    def __init__(self, sensor_name, default=None):
        super(OverridableVariable, self).__init__(sensor_name, default=default)
        self.overridden = WeakKeyDictionary()

    def register(self, client, instance, recipe_instance,
                 authtoken=None, callback=None):
        """Subscribes to the feed for the variable as well as the
        complementing override.
        """
        super(OverridableVariable, self).register(
            client, instance, recipe_instance, authtoken=authtoken,
            callback=callback)

        self.overridden[instance] = False
        self._subscribe(instance, recipe_instance,
                        variable_type=OVERRIDE_VARIABLE_TYPE)

    def __set__(self, obj, value):
        """override the __set__ function to check if an override is not in
        place on the variable before allowing to go to the normal __set__
        """
        # See if the controls are allowed to set this value at the moment.
        if self.overridden[obj]:
            return

        super(OverridableVariable, self).__set__(obj, value)

    def on_message(self, response):
        response_data = json.loads(response)
        sensor = response_data['sensor']
        variable_type = self.variable_types[sensor]
        recipe_instance = response_data['recipe_instance']
        subscriber_key = (sensor, variable_type, recipe_instance)

        # TODO(willjschmitt): Handle subscribers in client.
        if subscriber_key not in self.subscribers:
            return

        LOGGER.debug("Received updated value for sensor %s(%s), variable_type"
                     " %s, recipe_instance %s.", sensor, self.sensor_name,
                     variable_type, recipe_instance)
        subscriber = self.subscribers[subscriber_key]

        response_value = response_data['value']

        instance = subscriber['instance']

        if variable_type == OVERRIDE_VARIABLE_TYPE:
            self.overridden[instance] = bool(response_value)
            return
        else:
            return super(OverridableVariable, self).on_message(response)


class DataStreamer(object):
    """A streaming class to stream data periodically. A DataStreamer should be
    instantiated for every object that will be streaming data.

    Attributes:
        client: JouliaWebserverClient object for performing simple HTTP requests
            with a Joulia webserver.
        instance: The object streaming data, which should be polled regularly
            to send updates to the Joulia webserver.
        recipe_instance: The brewing instance the datastream is associated with.
        datastream_frequency: The period between automatic polling of data to be
            sent to the Joulia webserver. (milliseconds)
        attribute_to_name: A dictionary mapping attribute names to names used to
            store on server.
        id_to_attribute: A dictionary mapping the server variable id to
            attribute address (relative to instance).
        poller: The PeriodicCallback object that performs the async polling.
    """
    # TODO(will): This should be deprecated as soon as the calculated variables
    # can automatically send data like a ManagedVariable. Right now, there are
    # variables, which are calculated, which are not explicitly set, so they are
    # only evaluated when they are retrieved, which does not trigger an update
    # action. Since we have not event-driven basis. This class polls at a
    # regular interval and streams data regardless of change.

    def __init__(self, client, instance, recipe_instance, datastream_frequency):
        self.client = client
        self.instance = instance
        self.recipe_instance = recipe_instance
        self.datastream_frequency = datastream_frequency

        self.attribute_to_name = {}
        self.id_to_attribute = {}

        self.poller = ioloop.PeriodicCallback(
            self.post_data, self.datastream_frequency)

    def start(self):
        """Starts the polling process to stream data regularly."""
        self.poller.start()

    def stop(self):
        """Stops the polling process to stream data regularly."""
        self.poller.stop()

    def register(self, attr, name=None):
        """Registers variable with server

        Args:
            attr: Name of the attribute relative to `instance`, which should be
                polled regularly and sent to the server. Use dunderscores to
                indicate relationship. I.e: polling instance.foo.bar can be
                achieved by passing "foo__bar".
            name: Name to call the variable when sending to theserver. Defaults
                to ``attr`` if not provided.
        """
        if name is None:  # Default to attribute as the name
            name = attr

        LOGGER.debug("%r registering %s as %s for data streaming.",
                     self.instance, attr, name)

        identifier = self.client.identify(
            name, self.recipe_instance, VALUE_VARIABLE_TYPE)
        if identifier in self.id_to_attribute:
            # This makes sure we aren't overwriting anything
            raise AttributeError(
                '{} already exists in streaming service.'.format(name))

        self.attribute_to_name[attr] = name
        self.id_to_attribute[identifier] = attr

    def post_data(self):
        """Posts the current values of the data to the server"""
        LOGGER.debug('Data streamer %r sending data.', self)

        for sensor_id, attr in self.id_to_attribute.items():
            value = rgetattr(self.instance, attr)
            LOGGER.debug("Sending new value for %s: %s.", attr, value)
            self.client.update_sensor_value(
                self.recipe_instance, value, sensor_id)
