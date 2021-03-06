"""Global settings for configuring joulia-controller."""
import os

HOST = os.environ.get("JOULIA_WEBSERVER_HOST", None)
AUTHTOKEN = os.environ.get("JOULIA_WEBSERVER_AUTHTOKEN", None)

HTTP_PREFIX = "https"
WS_PREFIX = "wss"

DATASTREAM_FREQUENCY = 1000.  # mS

if os.name == "posix" and not os.environ.get("TRAVIS", False):
    LOGGING_DIR = "/var/log/joulia"
else:
    LOGGING_DIR = os.path.join(os.getcwd(), "log")

# Make sure the logging directory exists.
if not os.path.exists(LOGGING_DIR):
    os.makedirs(LOGGING_DIR)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(levelname)-8s] %(asctime)s %(name)-12s:%(lineno)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': os.path.join(LOGGING_DIR, 'joulia.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB logfiles.
            'backupCount': 10,
        },
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': True
        },
        'requests': {
            'level': 'ERROR',
            'handlers': ['console', 'file'],
            'propagate': False
        },
    },
}
