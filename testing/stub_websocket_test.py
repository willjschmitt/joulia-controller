"""Tests for the stub_websocket module."""

from tornado import gen
from tornado.ioloop import IOLoop
import unittest

from testing.stub_websocket import stub_websocket_connect
from testing.stub_websocket import StubWebSocketClientConnection


class TestStubWebsocketConnect(unittest.TestCase):
    """Tests for stub_websocket_connect function."""

    def test_succeeds(self):
        @gen.coroutine
        def connect():
            yield stub_websocket_connect("fake_url")

        IOLoop.current().run_sync(lambda: connect())

    def test_with_callback(self):
        counters = {"foo": 0}

        def foo(_):
            counters["foo"] += 1

        @gen.coroutine
        def connect():
            yield stub_websocket_connect("fake_url", callback=foo)

        IOLoop.current().run_sync(lambda: connect())

        self.assertEquals(counters["foo"], 1)


class TestStubWebSocketClientConnection(unittest.TestCase):
    """Tests for StubWebSocketClientConnection."""

    def test_create_succeeds(self):
        StubWebSocketClientConnection(IOLoop.current(), None)

    def test_write_message(self):
        ws_connection = StubWebSocketClientConnection(IOLoop.current(), None)
        ws_connection.write_message("foo")
        self.assertIn("foo", ws_connection.written_messages)
