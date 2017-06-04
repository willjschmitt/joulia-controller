"""Global settings for configuring joulia-controller."""
import os

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
