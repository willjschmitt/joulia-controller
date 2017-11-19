"""When run, posts to the joulia-webserver with an updated release.

Sends a POST to JOULIA_ENDPOINT with request details to be distributed to the
joulia-controllers to update to.
"""

import os
import requests

from brewery.brewhouse import Brewhouse


class Updater(object):
    """An updater to send controller update details to the Joulia webserver.

    Attributes:
        auth_token: The authentication token associate with the
            continuous_integration group on joulia-webserver.
        joulia_host: The host name with protocol prefix to send requests to.
    """
    RELEASE_ENDPOINT = '/brewery/api/joulia_controller_release/'
    STATE_ENDPOINT = '/brewery/api/brewing_state/'

    def __init__(self, auth_token, joulia_host):
        self.auth_token = auth_token
        self.joulia_host = joulia_host

    @property
    def _authentication_headers(self):
        return {'Authorization': 'Token {}'.format(self.auth_token)}

    def register_update(self, commit_hash):
        """Sends POST to joulia-webserver to indicate new release is available.

        Should be called as a deployment step for the master branch as determined by
        the .travis.yml.

        Args:
            commit_hash: The git commit hash to use for the new version.

        Returns:
            The primary key of the newly created update.
        """
        data = {'commit_hash': commit_hash}
        response = requests.post(
            '{}{}'.format(self.joulia_host, self.RELEASE_ENDPOINT), data=data,
            headers=self._authentication_headers)
        response.raise_for_status()
        return response.json()['id']

    def register_states(self, software_release_pk):
        """Sends all of the new states to the STATE_ENDPOINT.

        Provides joulia-webserver with the latest definitions of the controller
        states for the new software release, which can be used by web browsers,
        etc.

        Args:
            software_release_pk: The primary key for the new update registered
                with register_update.
        """
        for i, state in enumerate(Brewhouse.state_classes()):
            data = {
                'software_release': software_release_pk,
                'index': i,
                'name': state.NAME,
                'description': state.DESCRIPTION,
            }
            response = requests.post(
                '{}{}'.format(self.joulia_host, self.STATE_ENDPOINT),
                data=data,
                headers=self._authentication_headers)
            response.raise_for_status()


if __name__ == '__main__':
    updater = Updater(auth_token=os.environ['JOULIA_AUTH_TOKEN'],
                      joulia_host = os.environ['JOULIA_HOST'])
    software_release_pk = updater.register_update(
        commit_hash=os.environ['TRAVIS_COMMIT'])
    updater.register_states(software_release_pk)
