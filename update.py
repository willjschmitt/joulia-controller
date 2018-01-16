"""Manages software updates."""

import abc
import binascii
import logging
import os
import sys

from tornado import ioloop

LOGGER = logging.getLogger(__name__)


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

    def __init__(self, repo, client, brewhouse_pk,
                 system_restarter=restart_program):
        self.repo = repo
        self.client = client
        self.brewhouse_pk = brewhouse_pk
        self.system_restarter = system_restarter

        self._update_check_timer = ioloop.PeriodicCallback(
            self._check_version, self.UPDATE_CHECK_RATE)

    def watch(self):
        """Check for new versions periodically."""
        LOGGER.info("Starting watch for updates.")
        self._update_check_timer.start()

    def stop(self):
        """Stops checking for new versions periodically."""
        LOGGER.info("Ending watch for updates.")
        self._update_check_timer.stop()

    def _check_version(self):
        """Checks to see if there is any new version available. If there is a
        new version, downloads it, and restarts the process. Returns boolean if
        an update was required."""
        LOGGER.info("Checking for updates.")
        current_hash = binascii.hexlify(
            self.repo.head.object.binsha).decode('utf-8')
        latest_release = self.client.get_latest_joulia_controller_release()
        latest_hash = latest_release["commit_hash"]
        latest_release_id = latest_release['id']
        if latest_hash is None:
            LOGGER.info("No update hash found. Skipping update.")
            return False

        if latest_hash != current_hash:
            self._update(latest_hash, latest_release_id)
            return True

        brewhouse = self.client.get_brewhouse(self.brewhouse_pk)
        if latest_release_id != brewhouse['software_version']:
            self._update_server(latest_release_id)
            return True

    def _update(self, commit_hash, release_pk):
        """Updates the software to the provided SHA1 hash by performing a fetch
        followed by a checkout to that hash. Will restart the current process
        after.

        Args:
            commit_hash: The git commit hash to pull and checkout.
            release_pk: The primary key for the release to update to on the
                server.
        """
        LOGGER.warning("Updating software to hash %s.", commit_hash)
        self.repo.remotes.origin.fetch()
        commit = self.repo.commit(commit_hash)
        self.repo.git.checkout(commit)
        self._update_server(release_pk)
        self._restart()

    def _update_server(self, release_pk):
        """Updates the server with release updated to.

        Args:
            release_pk: The softare release pk updated to.
        """
        LOGGER.info("Updating server software version to %s.", release_pk)
        self.client.save_brewhouse_software_version(
            self.brewhouse_pk, release_pk)

    def _restart(self):
        """Ends the current process and restarts it with the same arguments
        that were provided to it. This is useful if the Python source files
        have been updated and need to be reloaded.
        """
        LOGGER.warning("Restarting system.")
        self.system_restarter()
