'''
Created on Apr 14, 2016

@author: William
'''

import datetime
import functools
import json
import logging
from weakref import WeakKeyDictionary,WeakSet
import gpiocrust
import pytz
import requests
from tornado import gen
from tornado import ioloop
from tornado.websocket import websocket_connect
import settings


LOGGER = logging.getLogger(__name__)

def subscribed(func):
    """Decorator function to check that the currently called instance is
    already subscribed to the server before making a call to send to the
    server
    """
    def func_wrapper(self,instance,*args,**kwargs):
        if instance in self.subscribed:
            return func(self,instance,*args,**kwargs)
        else:
            LOGGER.debug("Not yet subscribed.")

    return func_wrapper

def registered(func):
    """Decorator function to check that the currently called instance is
    already registered to the server before making a call to send to the
    server
    """
    def func_wrapper(self,instance,*args,**kwargs):
        if instance in self.registered:
            return func(self,instance,*args,**kwargs)
        else:
            LOGGER.debug("Not yet registered.")

    return func_wrapper

def rsetattr(obj, attr, val):
    """Sets nested attribute of child elements separating attribute path
    using a double underscore.

    Example: `attr` "foo__bar" sets the value at `obj.foo.bar`

    Args:
        obj: The object to set the value on.
        attr: The attribute path with dunderscores separating attribute paths
        val: value to set
    """
    pre, _, post = attr.rpartition('__')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)

def rgetattr(obj, attr):
    """Gets nested attribute of child elements separating attribute path
    using a double underscore.

    Example: `attr` "foo__bar" gets the value at `obj.foo.bar`

    Args:
        obj: The object to set the value on.
        attr: The attribute path with dunderscores separating attribute paths

    Returns: value at the attribute
    """
    return functools.reduce(getattr, [obj] + attr.split('__'))

class ManagedVariable(object):
    """Top level class to represent a managed variable that controls how
    the property is get or set for a given object.

    Meant to be an abstract class to help with binding variables with
    joulia-webserver.

    Attributes:
        default: Value to use for get's before any other process has set it
        sensor_name: The name of the sensor to use for handshakes with the
            server.
        data: A dictionary that maps an object to its instance's value. This
            is necessary, because this variable needs to be assigned at the
            class level in order for get/set to work correctly.
        authtokens: A dictionary that maps an object to its instance's
            authorization token.
    """

    data_identify_service = (settings.HTTP_PREFIX + ":" + settings.HOST
                             + "/live/timeseries/identify/")

    def __init__(self, sensor_name, default=None):
        self.default = default

        self.sensor_name = sensor_name
        self.recipe_instances = WeakKeyDictionary()
        self.data = WeakKeyDictionary()
        self.authtokens = WeakKeyDictionary()
        self.ids = WeakKeyDictionary()

        self.time_out_wait = 10
        self.time_out_counter = 0

        self.registered = WeakSet()
        self.subscribed = WeakSet()

    def __get__(self, obj, objtype):
        """Retrieves the current value for the object requested"""
        # Allows us to be able to access the property directly to get
        # at its methods like register, subscribe, etc.
        if obj is None:
            return self

        # Set the value to the default if it doesn't have a value yet
        if obj not in self.data:
            self.data[obj] = self.default

        return self.data.get(obj)

    def __set__(self, obj, value):
        """Sets the current value for the object requested"""
        self.data[obj] = value

    def register(self, instance, authtoken=None):
        """Registers this instance with the appropriate authentication.

        Args:
            instance: The instance to register.
            authtoken: The authentication token to authenticate with API
        """
        self.authtokens[instance] = authtoken
        
        self.registered.add(instance)

    def subscribe(self, instance, authtoken=None):
        """Subscribes this instance with the appropriate authentication.

        Args:
            instance: The instance to subscribe.
            authtoken: The authentication token to authenticate with API
        """
        self.authtokens[instance] = authtoken

        self.subscribed.add(instance)

    def authorization_headers(self, instance):
        """Generates authorization headers for the instance"""
        if self.authtokens[instance] is not None:
            headers = {'Authorization':'Token ' + self.authtokens[instance]}
        else:
            headers = {}
        return headers

    @subscribed
    @registered
    def identify(self, instance, recipe_instance):
        """Sends a request to the server based on the current recipe instance
        to identify the sensors id number, given the `sensor_name`

        Args:
            instance: The instance associated with the request (used for
                retrieving auth params)
            recipe_instance: The id number for the active recipe instance
            sensor_name: The string name for the sensor to request
                identification for

        Returns: The id number for the sensor.
        """
        data = {'recipe_instance':recipe_instance, 'name':self.sensor_name}

        request = self.post(instance, self.data_identify_service, data=data)
        self.ids[instance] = request.json()['sensor']
        return request.json()['sensor']

    def post(self, instance, url, *args, **kwargs):
        """Helper function to help make posts to the server but add time
        between requests incase there are issues so we don't pile up a ton
        of requests. Attaches authentication based on instance.

        Args:
            instance: the instance of the property we are working with
            url: Url to post to
            *args: To pass to `requests.post`
            **kwargs: To pass to `requests.post`
        """
        headers = self.authorization_headers(instance)
        try:
            request = requests.post(url, headers=headers,
                                    *args, **kwargs)
            request.raise_for_status()
        except requests.exceptions.ConnectionError:
            LOGGER.info("Server not there. Will retry later.")
            self.time_out_counter = self.time_out_wait
        except requests.exceptions.HTTPError:
            LOGGER.info("Server returned error status. Will retry later."
                        " (%s)",request.text)
            self.time_out_counter = self.time_out_wait

        return request

class SubscribableVariable(ManagedVariable):
    """A version of `ManagedVaraiable` that subscribes to a sensor stream
    on the server, and uses the values received to set the property.
    """

    def __init__(self, *args, **kwargs):
        super(SubscribableVariable, self).__init__(*args, **kwargs)
        self.callback = WeakKeyDictionary()

    def subscribe(self, instance, recipe_instance,
                  authtoken=None, callback=None):
        """Establishes the subscription information for the instance of
        this variable.

        Args:
            instance: The object this variable instance is a property of
            recipe_instance: The recipe_instance id from the server for the
                current recipe execution.
            authtoken: The authorization token used to authenticate activity
                with the server.
            callback: Function that should be called when an update is
                retreived. Useful if additional action should be taken
                to validate the servers's feedback.
        """
        super(SubscribableVariable, self).subscribe(instance,
                                                    authtoken=authtoken)

        self.callback[instance] = callback

        self.check_connectivity()

        self._subscribe(instance, self.sensor_name, recipe_instance)

    def _subscribe(self,instance,sensor_name,recipe_instance,
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
        if ((sensor_name, recipe_instance)) not in self.subscribers:
            LOGGER.info('Subscribing to %s, instance %s',
                        self.sensor_name,recipe_instance)

            id_sensor = self.identify(instance, recipe_instance)
            subscriber = {'descriptor':self, 'instance':instance,
                          'var_type':variable_type}
            self.subscribers[(id_sensor, recipe_instance)] = subscriber

            msg_string = json.dumps({'recipe_instance':recipe_instance,
                                     'sensor':id_sensor,
                                     'subscribe':True})
            self.websocket.write_message(msg_string)

    @gen.coroutine
    def check_connectivity(self):
        """Checks if a websocket connection is already established and
        starts a connection if it is not yet established.
        """
        # make sure we have a websocket established
        if self.websocket is None:
            websocket_address = (settings.WS_PREFIX + ":" + settings.HOST
                                 + "/live/timeseries/socket/")
            LOGGER.info('No websocket established. Establishing at %s',
                        websocket_address)
            callback = SubscribableVariable.on_message
            self.websocket = yield websocket_connect(websocket_address,
                                                     on_message_callback=callback)

    @classmethod
    def on_message(cls, response, *_, **__):
        """A generic callback to handle the response from a websocket
        communication back, which will receive the data and set it

        Args:
            response: The websocket response
            *_: not used, but just here to accept the websocket's call
            **__: not used, but just here to accept the websocket's call
        """
        if response is not None:
            response_data = json.loads(response)
            sensor = response_data['sensor']
            recipe_instance = response_data['recipe_instance']
            subscriber_key = (sensor, recipe_instance)
            subscriber = cls.subscribers[subscriber_key]

            response_value = response_data['value']

            if subscriber['var_type'] == 'value':
                current_value = subscriber['descriptor'].data[subscriber['instance']]
                current_type = type(current_value)
                subscriber['descriptor'].data[subscriber['instance']] = current_type(response_value)
                if (subscriber['instance'] in subscriber['descriptor'].callback
                    and subscriber['descriptor'].callback[subscriber['instance']] is not None):
                    callback = subscriber['descriptor'].callback[subscriber['instance']]
                    callback(response_value)
            elif subscriber['var_type'] == 'override':
                subscriber['descriptor'].overridden[subscriber['instance']] = bool(response_value)
        else:
            LOGGER.warning('Websocket closed unexpectedly.')

    websocket = None
    subscribers = {}


class StreamingVariable(ManagedVariable):
    """A version of `ManagedVaraiable` that publishes to a sensor stream
    on the server.
    """
    data_post_service = (settings.HTTP_PREFIX + ":" + settings.HOST
                         + "/live/timeseries/new/")

    def __init__(self, sensor_name, default=None):
        super(StreamingVariable, self).__init__(sensor_name, default=default)

        self.ids = WeakKeyDictionary()
        self.time_out_counter = 0

    def __set__(self, instance, value):
        """Sets the value to the current instance and sends the new value
        to the server.

        Args:
            instance: The instance to set the value for
            value: The value to set
        """
        super(StreamingVariable, self).__set__(instance, value)
        self.send_sensor_value(instance)

    def register(self, instance, recipe_instance, authtoken=None):
        """Registers the sensor with the server and retrieves the id for
        the sensor
        """
        LOGGER.debug('Registering %s',self.sensor_name)
        super(StreamingVariable, self).register(instance,
                                                authtoken=authtoken)

        self.recipe_instances[instance] = recipe_instance
        self.identify(instance, recipe_instance)

    @registered
    def send_sensor_value(self, instance):
        """Sends the current sensor value for the sensor to the server

        Args:
            instance: The instance to send the value for.
        """
        if self.time_out_counter > 0:
            self.time_out_counter -= 1
        else:
            LOGGER.debug('Data streamer %r sending data for %s.',
                         self, self.sensor_name)

            # send the data
            sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

            value = self.clean_value(self.data[instance])
            data = {
                'time':sample_time,
                'recipe_instance':self.recipe_instances[instance],
                'value': value,
                'sensor':self.ids[instance]
            }
            self.post(instance, self.data_post_service, data=data)

    @staticmethod
    def clean_value(value):
        """Returns a cleaned value that will be appropriately interpreted.
        """
        if value is None: # TODO: make server accept None
            value = 0
        if value is True:
            value = 1
        if value is False:
            value = 0

        return value

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

    def subscribe(self, instance, recipe_instance,
                  authtoken=None, callback=None):
        """Subscribes to the feed for the variable as well as the
        complementing override.

        Args:
            instance: The instance subscribe
            recipe_instance: the recipe instance for subscription
            authtoken: The authentication token to communicate over the API
            callback: A function to be called after new data is received
                from the server.
        """
        super(OverridableVariable, self).subscribe(instance,
                                                   authtoken=authtoken)

        self.overridden[instance] = False
        super(OverridableVariable, self).subscribe(instance, recipe_instance,
                                                   callback=callback)

        self._subscribe(instance, self.sensor_name + "Override",
                        recipe_instance, 'override')

        self.register(instance, recipe_instance)

    def __set__(self, obj, value):
        '''override the __set__ function to check if an override is not in
        place on the variable before allowing to go to the normal __set__
        '''
        if not self.overridden.get(obj):
            super(OverridableVariable, self).__set__(obj, value)
            self.send_sensor_value(obj)

class DataStreamer(object):
    """A streaming class to stream data periodically. Has an internal
    clock to send data at the frequency found in ``settings.datastream_frequency``
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

        ioloop.PeriodicCallback(self.post_data, settings.DATASTREAM_FREQUENCY).start()

    def register(self, attr, name=None):
        """Registers variable with server

        Args:
            attr: Name of the attribute to register with the server
            name: Name to register the variable as with the server. Defaults
                to ``attr`` if not provided.
        """
        if name is None: # default to attribute as the name
            name = attr
        if name in self.sensor_map:
            # this makes sure we arent overwriting anything
            raise AttributeError('{} already exists in streaming service.'
                                 ''.format(name))
        # map the attribute to the server var name
        self.sensor_map[name] = {'attr':attr}

    @registered
    def post_data(self):
        """Posts the current values of the data to the server"""
        if self.time_out_counter > 0:
            self.time_out_counter -= 1
        else:
            LOGGER.debug('Data streamer %r sending data.',self)

            # post temperature updates to server
            sample_time = datetime.datetime.now(tz=pytz.utc).isoformat()

            for sensor_name, sensor in self.sensor_map.iteritems():
                # get the sensor ID if we dont have it already
                if 'id' not in sensor:
                    try:
                        data = {'recipe_instance':self.recipe_instance,
                                'name':sensor_name}
                        # TODO: add authorization
#                         if self.authtokens[instance] is not None:
#                             headers = {'Authorization':'Token ' + self.authtokens[instance]}
#                         else:
#                             headers = {}
                        headers = {}

                        request = requests.post(self.data_identify_service,
                                          data=data, headers=headers)
                        request.raise_for_status()
                    except requests.exceptions.ConnectionError:
                        LOGGER.info("Server not there. Will retry later.")
                        self.time_out_counter = self.time_out_wait
                        break
                    except requests.exceptions.HTTPError:
                        LOGGER.info("Server returned error status. Will "
                                    "retry later. (%s)",request.text)
                        self.time_out_counter = self.time_out_wait
                        break

                    sensor['id'] = request.json()['sensor']

                # send the data
                try:
                    value = rgetattr(self.streaming_class, sensor['attr'])
                    if value is None: # TODO: make server accept None
                        value = "0"
                    if value is True:
                        value = 'true'
                    if value is False:
                        value = 'false'
                    data = {'time':sample_time,
                          'recipe_instance':self.recipe_instance,
                          'value': value,
                          'sensor':sensor['id']}
                    # TODO: add authorization
#                     if self.authtokens[instance] is not None:
#                         headers = {'Authorization':'Token ' + self.authtokens[instance]}
#                     else:
#                         headers = {}
                    headers = {}
                    request = requests.post(self.data_post_service,
                                      data=data, headers=headers)
                    request.raise_for_status()
                except requests.exceptions.ConnectionError:
                    LOGGER.info("Server not there. Will retry later.")
                    self.time_out_counter = self.time_out_wait
                    break
                except requests.exceptions.HTTPError:
                    LOGGER.info("Server returned error status. Will retry "
                                "later. (%s)",request.text)
                    self.time_out_counter = self.time_out_wait
                    break

GPIO_MOCK_API_ACTIVE = 'gpio_mock' in dir(gpiocrust)
