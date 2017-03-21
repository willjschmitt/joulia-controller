"""Mock interface to the tornado.http_client.AsyncHTTPClient class."""

import json


class StubAsyncHTTPClient(object):
    """Stubs the AsyncHTTPClient from the tornado.http_client library."""

    def __init__(self):
        self.error = False
        self.messages = {}

    def fetch(self, url, callback, method, body):
        response = StubAsyncHTTPClientResponse(self.error, self.messages)
        callback(response)


class StubAsyncHTTPClientResponse(object):
    def __init__(self, error, messages):
        self.error = error
        if not self.error:
            self.body = json.dumps({"messages": messages})
