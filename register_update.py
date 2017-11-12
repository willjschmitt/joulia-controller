"""When run, posts to the joulia-webserver with an updated release.

Sends a POST to JOULIA_ENDPOINT with request details to be distributed to the
joulia-controllers to update to.
"""

import os
import requests


JOULIA_ENDPOINT = '/brewery/api/joulia_controller_release/'


def register_update(commit_hash, auth_tokem, joulia_host):
    """Sends POST to joulia-webserver to indicate new release is available.

    Should be called as a deployment step for the master branch as determined by
    the .travis.yml.

    Args:
        commit_hash: The git commit hash to use for the new version.
        auth_token: The authentication token associate with the
            continuous_integration group on joulia-webserver.
        joulia_host: The host name with protocol prefix to send requests to.
    """
    data = {'commit_hash': commit_hash}
    auth_headers = {'Authorization': 'Token {}'.format(auth_token)}
    response = requests.post('{}{}'.format(joulia_host, JOULIA_ENDPOINT),
                             data=data, headers=auth_headers)
    response.raise_for_status()


if __name__ == '__main__':
    commit_hash = os.environ['TRAVIS_COMMIT']
    auth_token = os.environ['JOULIA_AUTH_TOKEN']
    joulia_host = os.environ['JOULIA_HOST']
    register_update(commit_hash, auth_token, joulia_host)
