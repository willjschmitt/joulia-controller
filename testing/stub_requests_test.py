"""Tests for the stub_requests module."""

import unittest

from testing.stub_requests import StubRequests
from testing.stub_requests import StubResponse


class TestStubRequests(unittest.TestCase):
    """Tests for the StubRequests class."""

    def setUp(self):
        self.requests = StubRequests()

    def test_post(self):
        pass


class TestStubResponse(unittest.TestCase):
    """Tests for the StubResponse class."""

    def test_json(self):
        response = StubResponse('{"foo":"bar"}', 200, "OK")
        got = response.json()
        want = {"foo":"bar"}
        self.assertEquals(got, want)
