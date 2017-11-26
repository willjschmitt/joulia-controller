"""Mock interface to the tornado.http_client.AsyncHTTPClient class."""

# TODO(willjschmitt): Python 3.4 does not support HTTPStatus, so we mock it up
# for now, since it's only used for testing.
# from http import HTTPStatus

import json
from unittest.mock import Mock

from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPResponse


# TODO(willjschmitt): Python 3.4 does not support HTTPStatus, so we mock it up
# for now, since it's only used for testing.
HTTPStatus = Mock()  # pylint: disable=invalid-name
HTTPStatus.OK = 200


class StubAsyncHTTPClient(AsyncHTTPClient):  # pylint: disable=abstract-method
    """Stubs the AsyncHTTPClient from the tornado.http_client library."""

    def __init__(self):
        self.error = False
        self.status_code = HTTPStatus.OK
        self.response = {}

        self.responses = []
        self._response_count = 0

    def fetch(self, request, callback=None, raise_error=True, **kwargs):
        del request, raise_error, kwargs
        # If a list of multiple responses has not been provided, fall back onto
        # the single response.
        if not self.responses:
            if self.response is not None:
                callback(StubAsyncHTTPClientResponse(
                    self.status_code, self.error, self.response))
        # Otherwise use the list of responses.
        else:
            response = self.responses[self._response_count]
            self._response_count += 1
            if response is not None:
                callback(StubAsyncHTTPClientResponse(
                    response.get("status_code", HTTPStatus.OK),
                    response.get("error", None), response["response"]))


class StubAsyncHTTPClientResponse(HTTPResponse):
    """Stubs the response from an AsyncHTTPClient for StubAsyncHTTPClient."""
    def __init__(self, status_code, error, response):  # pylint: disable=super-init-not-called
        self.error = error
        self.code = status_code
        if not self.error:
            self._body = json.dumps(response)

    @property
    def body(self):
        return self._body

    def rethrow(self):
        if self.error:
            raise self.error
