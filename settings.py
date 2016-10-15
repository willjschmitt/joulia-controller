'''
Created on Apr 30, 2016

@author: William
'''
import os

BREWHOUSE_ID = os.environ['JOULIA_WEBSERVER_BREWHOUSE_ID']

HOST = os.environ["JOULIA_WEBSERVER_HOST"]
AUTHTOKEN = os.environ["JOULIA_WEBSERVER_AUTHTOKEN"]

HTTP_PREFIX = "http"
WS_PREFIX = "ws"

DATASTREAM_FREQUENCY = 1000. #mS

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'root': {
            'level': 'INFO',
            'handlers': ['console'],
            'propogate': True
        },
        'requests': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propogate': False
        },
    },
}
