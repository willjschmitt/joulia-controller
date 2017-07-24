"""Manages software updates."""

import os
import sys


def restart_program():
    """Ends the current process and restarts it with the same arguments that
    were provided to it.
    """
    os.execv(sys.executable, ['python'] + sys.argv)


class UpdateManager(object):
    """Checks for new versions available of software and updates them when
    they are.

    Attributes:
        repo: A gitpython repo for managing the git repository for the software.
        client: A joulia-webserver client for querying the available software
            versions.
        system_restarter: A function that can be called with no arguments to
            restart the currently running program.
    """
    def __init__(self, repo, client, system_restarter=restart_program):
        self.repo = repo
        self.client = client
        self.system_restarter = system_restarter

    def check_version(self):
        """Checks to see if there is any new version available. If there is a
        new version, downloads it, and restarts the process. Returns boolean if
        an update was required."""
        current_hash = self.repo.head.binsha.hex()
        latest_release = self.client.get_latest_joulia_controller_release()
        latest_hash = latest_release["commit_hash"]
        if latest_hash is not None and latest_hash != current_hash:
            self.update(latest_release["commit_hash"])
            return True
        return False

    def update(self, commit_hash):
        """Updates the software to the provided SHA1 hash by performing a fetch
        followed by a checkout to that hash. Will restart the current process
        after.
        """
        self.repo.remotes.origin.fetch()
        self.repo.head.checkout(commit_hash, ".")
        self.restart()

    def restart(self):
        """Ends the current process and restarts it with the same arguments
        that were provided to it. This is useful if the Python source files
        have been updated and need to be reloaded.
        """
        self.system_restarter()
