"""Tests for the stub_websocket module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes,blacklisted-name

import unittest

from tornado import gen
from tornado.ioloop import IOLoop

from testing.stub_websocket import stub_websocket_connect
from testing.stub_websocket import StubWebSocketClientConnection


class TestStubWebsocketConnect(unittest.TestCase):
    """Tests for stub_websocket_connect function."""

    def test_succeeds(self):  # pylint: disable=no-self-use
        @gen.coroutine
        def connect():
            yield stub_websocket_connect("fake_url")

        IOLoop.current().run_sync(connect)

    def test_with_callback(self):
        counters = {"foo": 0}

        def foo(_):
            counters["foo"] += 1

        @gen.coroutine
        def connect():
            yield stub_websocket_connect("fake_url", callback=foo)

        IOLoop.current().run_sync(connect)

        self.assertEqual(counters["foo"], 1)


class TestStubWebSocketClientConnection(unittest.TestCase):
    """Tests for StubWebSocketClientConnection."""

    def test_create_succeeds(self):  # pylint: disable=no-self-use
        StubWebSocketClientConnection(IOLoop.current(), None)

    def test_write_message(self):
        ws_connection = StubWebSocketClientConnection(IOLoop.current(), None)
        ws_connection.write_message("foo")
        self.assertIn("foo", ws_connection.written_messages)
