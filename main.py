'''
Created on Apr 5, 2016

@author: William
'''
import logging.config
from tornado import ioloop, gen
from brewery import brewing
import settings

logging.basicConfig(level=logging.DEBUG)
logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)

def main():
    """Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance."""
    brewing.Brewhouse(AUTHTOKEN=settings.AUTHTOKEN)
    LOGGER.info('Brewery initialized.')

    ioloop.IOLoop.instance().start()


def watch_for_start(self):
    """Makes a long-polling request to joulia-webserver to check
    if the server received a request to start a brewing session.

    Once the request completes, the internal method
    handle_start_request is executed.
    """

    def handle_start_request(response):
        """Handles the return from the long-poll request. If the
        request had an error (like timeout), it launches a new
        request. If the request succeeds, it fires the startup
        logic for this Brewhouse
        """
        if response.error:
            logging.error(response)
            self.watch_for_start()
        else:
            LOGGER.info("Got command to start")
            response = json_decode(response.body)
            messages = response['messages']
            self.recipe_instance = messages['recipe_instance']
            self.start_brewing()
            self.watch_for_end()

    http_client = AsyncHTTPClient()
    post_data = {'brewhouse': settings.BREWHOUSE_ID}
    uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/start/"
    headers = {'Authorization': 'Token ' + self.authtoken}
    http_client.fetch(uri, handle_start_request,
                      headers=headers,
                      method="POST",
                      body=urllib.urlencode(post_data))


def watch_for_end(self):
    """Makes a long-polling request to joulia-webserver to check
    if the server received a request to end the brewing session.

    Once the request completes, the internal method
    handle_end_request is executed.
    """

    def handle_end_request(response):
        """Handles the return from the long-poll request. If the
        request had an error (like timeout), it launches a new
        request. If the request succeeds, it fires the termination
        logic for this Brewhouse
        """
        if response.error:
            self.watch_for_end()
        else:
            self.end_brewing()

    http_client = AsyncHTTPClient()
    post_data = {'brewhouse': settings.BREWHOUSE_ID}
    uri = HTTP_PREFIX + ":" + HOST + "/live/recipeInstance/end/"
    headers = {'Authorization': 'Token ' + self.authtoken}
    http_client.fetch(uri, handle_end_request,
                      headers=headers,
                      method="POST",
                      body=urllib.urlencode(post_data))

if __name__ == "__main__":
    main()
