"""Stubs out requests module for mocking data responses."""

import json
import requests


class StubRequests(object):
    """Stub requests service for mocking requests to a server without actually
    committing them. Responds to any requests with the entry for the request URL
    in response_map. If the URL is not in the response map, responds with
    response_string.
    """
    def __init__(self):
        self.response_string = None
        self.response_map = {}
        self.server_there = True
        self.status_code = 200
        self.reason = "OK"

    def response(self, url):
        """Gets the response stored for the given url."""
        return self.response_map.get(url, self.response_string)

    def post(self, url, headers=None, *args, **kwargs):
        """Mocks the post function in the requests library."""
        del headers, args, kwargs
        if not self.server_there:
            raise requests.exceptions.ConnectionError()
        return StubResponse(self.response(url), self.status_code, self.reason)

    def get(self, url, headers=None, *args, **kwargs):
        """Mocks the get function in the requests library."""
        del headers, args, kwargs
        if not self.server_there:
            raise requests.exceptions.ConnectionError()
        return StubResponse(self.response(url), self.status_code, self.reason)


class StubResponse(requests.Response):
    """A fake response to be created by StubRequests.

    Inherits from requests.Response to automatically provide niceties like the
    raise_from_status method.
    """
    def __init__(self, response_string, status_code, reason):
        super(StubResponse, self).__init__()

        self.response_string = response_string
        self.status_code = status_code
        self.reason = reason

    def json(self, **kwargs):
        del kwargs
        return json.loads(self.response_string)
