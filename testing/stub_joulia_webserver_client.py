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
        self.update_sensor_value_posts = []
        self.mash_points = []
        self.recipe_instance = None
        self.recipe = None

    def identify(self, sensor_name, recipe_instance):
        result = self.identifier
        self.identifier += 1
        return result

    def update_sensor_value(self, recipe_instance, value, sensor):
        update = {"recipe_instance": recipe_instance,
                  "value": value,
                  "sensor": sensor}
        self.update_sensor_value_posts.append(update)
        return

    def get_mash_points(self, recipe_instance_pk):
        return self.mash_points

    def get_recipe_instance(self, recipe_instance_pk):
        return self.recipe_instance, \
            "recipe_instance must be set on StubJouliaHTTPClient if using" \
            " get_recipe_instance"

    def get_recipe(self, recipe_pk):
        assert self.recipe is not None, \
            "recipe must be set on StubJouliaHTTPClient if using get_recipe"
        return self.recipe


class StubJouliaWebsocketClient(JouliaWebsocketClient):
    """Stub class for JouliaWebsocketClient.
    """
    def __init__(self, address, http_client, auth_token=None):
        self._websocket_connect = stub_websocket_connect

        super(StubJouliaWebsocketClient, self).__init__(
            address, http_client, auth_token=auth_token)
