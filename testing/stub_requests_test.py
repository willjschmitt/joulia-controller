"""Tests for the stub_requests module."""

import requests
import unittest

from testing.stub_requests import StubRequests
from testing.stub_requests import StubResponse


class TestStubRequests(unittest.TestCase):
    """Tests for the StubRequests class."""

    def setUp(self):
        self.requests = StubRequests()

    def test_post(self):
        response = self.requests.post("fake_url")
        self.assertIsInstance(response, StubResponse)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.reason, "OK")

    def test_post_server_not_there(self):
        self.requests.server_there = False
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.requests.post("fake_url")


class TestStubResponse(unittest.TestCase):
    """Tests for the StubResponse class."""

    def test_json(self):
        response = StubResponse('{"foo":"bar"}', 200, "OK")
        got = response.json()
        want = {"foo":"bar"}
        self.assertEquals(got, want)
