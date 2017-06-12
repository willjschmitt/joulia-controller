"""Mock interface to the tornado.http_client.AsyncHTTPClient class."""

import json


class StubAsyncHTTPClient(object):
    """Stubs the AsyncHTTPClient from the tornado.http_client library."""

    def __init__(self):
        self.error = False
        self.response = {}

        self.responses = []
        self._response_count = 0

    def fetch(self, url, callback, method, body, headers=None):
        # If a list of multiple responses has not been provided, fall back onto
        # the single response.
        if not self.responses:
            if self.response is not None:
                callback(StubAsyncHTTPClientResponse(self.error, self.response))
        # Otherwise use the list of responses.
        else:
            response = self.responses[self._response_count]
            self._response_count += 1
            if response is not None:
                callback(StubAsyncHTTPClientResponse(self.error, response))


class StubAsyncHTTPClientResponse(object):
    def __init__(self, error, response):
        self.error = error
        if not self.error:
            self.body = json.dumps(response)
