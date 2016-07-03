'''
Created on Apr 5, 2016

@author: William
'''

from brewery import brewing

from tornado import ioloop
from tornado import gen

import logging
logging.basicConfig(level=logging.DEBUG)

from settings import LOGGING_CONFIG

import logging.config
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

@gen.coroutine
def main():
    brewing.brewery()
    logger.info('Brewery initialized.')
    ioloop.IOLoop.current().start()
    
if __name__ == "__main__":
    main()