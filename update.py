"""Manages software updates."""

import abc
import binascii
import os
import sys

from tornado import ioloop


def restart_program():
    """Ends the current process and restarts it with the same arguments that
    were provided to it.
    """
    os.execv(sys.executable, ['python'] + sys.argv)


class UpdateManager(abc.ABC):
    """Abstract class for software updating."""

    @abc.abstractmethod
    def watch(self):
        """Check for new versions periodically."""
        ...

    @abc.abstractmethod
    def stop(self):
        """Stops checking for new versions periodically."""
        ...


class GitUpdateManager(UpdateManager):
    """Updates software based on git commits compared to versions on server.

    Attributes:
        repo: A gitpython repo for managing the git repository for the software.
        client: A joulia-webserver client for querying the available software
            versions.
        system_restarter: A function that can be called with no arguments to
            restart the currently running program.
    """

    # Rate to check for updates. Set to 30 seconds.
    UPDATE_CHECK_RATE = 30 * 1000  # milliseconds

    def __init__(self, repo, client, system_restarter=restart_program):
        self.repo = repo
        self.client = client
        self.system_restarter = system_restarter

        self._update_check_timer = ioloop.PeriodicCallback(
            self._check_version, self.UPDATE_CHECK_RATE)

    def watch(self):
        """Check for new versions periodically."""
        self._update_check_timer.start()

    def stop(self):
        """Stops checking for new versions periodically."""
        self._update_check_timer.stop()

    def _check_version(self):
        """Checks to see if there is any new version available. If there is a
        new version, downloads it, and restarts the process. Returns boolean if
        an update was required."""
        current_hash = binascii.hexlify(
            self.repo.head.object.binsha).decode('utf-8')
        latest_release = self.client.get_latest_joulia_controller_release()
        latest_hash = latest_release["commit_hash"]
        if latest_hash is not None and latest_hash != current_hash:
            self._update(latest_release["commit_hash"])
            return True
        return False

    def _update(self, commit_hash):
        """Updates the software to the provided SHA1 hash by performing a fetch
        followed by a checkout to that hash. Will restart the current process
        after.
        """
        self.repo.remotes.origin.fetch()
        commit = self.repo.commit(commit_hash)
        self.repo.git.checkout(commit)
        self._restart()

    def _restart(self):
        """Ends the current process and restarts it with the same arguments
        that were provided to it. This is useful if the Python source files
        have been updated and need to be reloaded.
        """
        self.system_restarter()
