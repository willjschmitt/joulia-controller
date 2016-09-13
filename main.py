'''
Created on Apr 5, 2016

@author: William
'''

from brewery import brewing

from tornado import ioloop,gen

import settings

import logging.config
logging.basicConfig(level=logging.DEBUG)
logging.config.dictConfig(settings.LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)

@gen.coroutine
def main():
    '''Main routine is for running as standalone controller on embedded
    hardware. Loads settings from module and env vars, and launches a
    controller instance.'''
    brewing.Brewhouse(authtoken=settings.authtoken)
    LOGGER.info('Brewery initialized.')
    
    ioloop.IOLoop.instance().start()
    

if __name__ == "__main__":
    main()
