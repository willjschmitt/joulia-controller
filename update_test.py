"""Tests for the update module."""

import unittest

from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from update import UpdateManager


class StubRepo(object):
    """Stub object for a gitpython Repo object."""
    def __init__(self):
        self.head = StubHead()
        self.remotes = StubRemotes()
        self.git = StubGit()

    def commit(self, commit_hash):
        return StubCommit()


class StubHead(object):
    def __init__(self):
        self.object = StubObject()


class StubObject(object):
    def __init__(self):
        self.binsha = bytearray.fromhex('abcd'*10)


class StubRemotes(object):
    def __init__(self):
        self.origin = StubOrigin()


class StubOrigin(object):
    def fetch(self):
        pass


class StubCommit(object):
    pass


class StubGit(object):
    def checkout(self, commit):
        pass


def stub_system_restarter():
    """Fake function that just returns nothing to act like a "system restarter".
    """


class TestUpdateManager(unittest.TestCase):
    def setUp(self):
        self.repo = StubRepo()
        self.client = StubJouliaHTTPClient("http://fakehost")
        self.update_manager = UpdateManager(
            self.repo, self.client, system_restarter=stub_system_restarter)

    def test_check_version_no_new_version(self):
        self.client.latest_controller_release = {
           "commit_hash": "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"}
        updated = self.update_manager.check_version()
        self.assertFalse(updated)

    def test_check_version_no_version(self):
        self.client.latest_controller_release = {
           "commit_hash": None}
        updated = self.update_manager.check_version()
        self.assertFalse(updated)

    def test_check_version_new_version(self):
        self.client.latest_controller_release = {
           "commit_hash": "dcbadcbadcbadcbadcbadcbadcbadcbadcbadcba"}
        updated = self.update_manager.check_version()
        self.assertTrue(updated)
