"""Stubs for the Joulia Webserver clients found in joulia_webserver_client"""

from joulia_webserver.client import JouliaHTTPClient
from joulia_webserver.client import JouliaWebsocketClient
from testing.stub_websocket import stub_websocket_connect


class StubJouliaHTTPClient(JouliaHTTPClient):
    """Stub class for JouliaHTTPClient.

    Attributes:
        identifier: The id number to be returned by the identify method as the
            mocked response. Gets monotonically increased every time identify
            is called so larger systems can work. Unittests should override
            identifier every time it is expected to change.
    """
    def __init__(self, address, auth_token=None):
        super(StubJouliaHTTPClient, self).__init__(
            address, auth_token=auth_token)
        self.identifier = 0
        self.variable_type = "value"
        self.update_sensor_value_posts = []
        self.mash_points = []
        self.recipe_instance = None
        self.recipe = None
        self.latest_joulia_controller_release = None
        self.brewhouse = None

    def identify(self, sensor_name, recipe_instance):
        result = self.identifier
        self.identifier += 1
        return result, self.variable_type

    def update_sensor_value(self, recipe_instance, value, sensor):
        update = {"recipe_instance": recipe_instance,
                  "value": value,
                  "sensor": sensor}
        self.update_sensor_value_posts.append(update)
        return

    def get_mash_points(self, recipe_instance_pk):
        return self.mash_points

    def get_recipe_instance(self, recipe_instance_pk):
        assert self.recipe_instance is not None, \
            "recipe_instance must be set on StubJouliaHTTPClient if using" \
            " get_recipe_instance"
        return self.recipe_instance

    def get_recipe(self, recipe_pk):
        assert self.recipe is not None, \
            "recipe must be set on StubJouliaHTTPClient if using get_recipe"
        return self.recipe

    def get_latest_joulia_controller_release(self):
        assert self.latest_joulia_controller_release is not None, \
            "latest_joulia_controller_release must be set on" \
            "StubJouliaHTTPClient if using get_latest_joulia_controller_release"
        return self.latest_joulia_controller_release

    def get_brewhouse(self, brewhouse_pk):
        assert self.brewhouse is not None, \
            "brewhouse must be set on StubJouliaHTTPClient if using" \
            "get_brewhouse"
        return self.brewhouse


class StubJouliaWebsocketClient(JouliaWebsocketClient):
    """Stub class for JouliaWebsocketClient.
    """
    def __init__(self, address, http_client, auth_token=None):
        self._websocket_connect = stub_websocket_connect

        super(StubJouliaWebsocketClient, self).__init__(
            address, http_client, auth_token=auth_token)
