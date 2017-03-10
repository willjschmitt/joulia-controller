"""Stubs for the Joulia Webserver clients found in joulia_webserver_client"""

from joulia_webserver_client import JouliaHTTPClient
from joulia_webserver_client import JouliaWebsocketClient


class StubJouliaHTTPClient(JouliaHTTPClient):
    """Stub class for JouliaHTTPClient.

    Attributes:
        identifier: The id number to be returned by the identify method as the
            mocked response.
    """
    def __init__(self, address, auth_token=None):
        super(StubJouliaHTTPClient, self).__init__(
            address, auth_token=auth_token)
        self.identifier = 0

    def identify(self, sensor_name, recipe_instance):
        return self.identifier


class StubJouliaWebsocketClient(JouliaWebsocketClient):
    """Stub class for JouliaWebsocketClient.
    """
    def __init__(self, address, http_client, auth_token=None):
        super(StubJouliaWebsocketClient, self).__init__(
            address, http_client, auth_token=auth_token)
