"""Stub module for mocking websocket actions for unit tests. Mocks
websocket_connect and returning a WebSocketClientConnection.
"""
import datetime

from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop


def stub_websocket_connect(url, io_loop=None, callback=None,
                           connect_timeout=None, on_message_callback=None,
                           compression_options=None):
    """A stub version of tornado.websocket.websocket_connect for use in unit
    tests."""
    if io_loop is None:
        io_loop = IOLoop.current()
    k_request = None
    conn = StubWebSocketClientConnection(
        io_loop, k_request, on_message_callback=on_message_callback,
        compression_options=compression_options)
    if callback is not None:
        io_loop.add_future(conn.connect_future, callback)
    return conn.connect_future


class StubWebSocketClientConnection(object):
    """A stub version of tornado.websocket.WebSocketClientConnection for use in
    unit tests.

    Attributes:
        TIMEOUT: class constant, which should be overridden in subclasses, in
            order to vary the time from when the class is instantiated until the
            returned future is resolved.
        connect_future: the Future resolved when the client "connection" is
            made.
        written_messages: a list of messages passed to the write_message
            method to see they have been received.
    """
    TIMEOUT = datetime.timedelta(milliseconds=0)

    def __init__(self, io_loop, request, on_message_callback=None,
                 compression_options=None):
        self.connect_future = TracebackFuture()
        self.written_messages = []

        io_loop.add_timeout(self.TIMEOUT, self._complete)

    def _complete(self):
        self.connect_future.set_result(self)

    def write_message(self, message):
        self.written_messages.append(message)
