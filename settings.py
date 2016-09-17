'''
Created on Apr 30, 2016

@author: William
'''
import os

BREWHOUSE_ID = 1

HOST = os.environ["joulia-webserver-HOST"]
AUTHTOKEN = os.environ["joulia-webserver-AUTHTOKEN"]

HTTP_PREFIX = "http"
WS_PREFIX = "ws"

DATASTREAM_FREQUENCY = 1000. #mS

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'root': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propogate': True
        },
        'utils': {
            'level': 'ERROR',
        },
        'requests': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propogate': False
        },
    },
}
