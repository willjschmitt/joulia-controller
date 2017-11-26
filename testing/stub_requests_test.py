"""Tests for the stub_requests module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes

import unittest
import requests

from testing.stub_requests import StubRequests
from testing.stub_requests import StubResponse


class TestStubRequests(unittest.TestCase):
    """Tests for the StubRequests class."""

    def setUp(self):
        self.requests = StubRequests()

    def test_post(self):
        response = self.requests.post("fake_url")
        self.assertIsInstance(response, StubResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")

    def test_post_uses_url_specific_response(self):
        self.requests.response_string = "should never see this"
        self.requests.response_map["fake_url1"] = '{"fake response":1}'
        self.requests.response_map["fake_url2"] = '{"fake response":2}'

        response = self.requests.post("fake_url1")
        self.assertIsInstance(response, StubResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")
        self.assertEqual(response.json(), {"fake response": 1})

        response = self.requests.post("fake_url2")
        self.assertIsInstance(response, StubResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")
        self.assertEqual(response.json(), {"fake response": 2})

    def test_post_server_not_there(self):
        self.requests.server_there = False
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.requests.post("fake_url")

    def test_get(self):
        response = self.requests.get("fake_url")
        self.assertIsInstance(response, StubResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")

    def test_get_server_not_there(self):
        self.requests.server_there = False
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.requests.get("fake_url")


class TestStubResponse(unittest.TestCase):
    """Tests for the StubResponse class."""

    def test_json(self):
        response = StubResponse('{"foo":"bar"}', 200, "OK")
        got = response.json()
        want = {"foo":"bar"}
        self.assertEqual(got, want)
