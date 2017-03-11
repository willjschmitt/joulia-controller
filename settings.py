"""Global settings for configuring joulia-controller."""
import os

BREWHOUSE_ID = os.environ.get('JOULIA_WEBSERVER_BREWHOUSE_ID', None)

HOST = os.environ.get("JOULIA_WEBSERVER_HOST", None)
AUTHTOKEN = os.environ.get("JOULIA_WEBSERVER_AUTHTOKEN", None)

HTTP_PREFIX = "http"
WS_PREFIX = "ws"

DATASTREAM_FREQUENCY = 1000.  # mS

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
            'level': 'DEBUG',
        },
        'requests': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propogate': False
        },
    },
}
