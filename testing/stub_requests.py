"""Stubs out requests module for mocking data responses."""

import json
import requests


class StubRequests(object):
    """Stub requests service for mocking requests to a server without actually
    committing them.
    """
    def __init__(self):
        self.response_string = None
        self.server_there = True
        self.status_code = 200
        self.reason = "OK"

    def post(self, url, headers=None, *args, **kwargs):
        if not self.server_there:
            raise requests.exceptions.ConnectionError()
        return StubResponse(self.response_string, self.status_code, self.reason)


class StubResponse(requests.Response):
    def __init__(self, response_string, status_code, reason):
        super(StubResponse, self).__init__()

        self.response_string = response_string
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.response_string)
