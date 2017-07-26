"""Global settings for configuring joulia-controller."""
import os

HOST = os.environ.get("JOULIA_WEBSERVER_HOST", None)
AUTHTOKEN = os.environ.get("JOULIA_WEBSERVER_AUTHTOKEN", None)

HTTP_PREFIX = "http"
WS_PREFIX = "ws"

DATASTREAM_FREQUENCY = 1000.  # mS

if os.name == "posix" and os.environ.get("TRAVIS", False):
    LOGGING_DIR = "/var/log/joulia"
else:
    LOGGING_DIR = os.path.join(os.getcwd(), "log")

# Make sure the logging directory exists.
if not os.path.exists(LOGGING_DIR):
    os.makedirs(LOGGING_DIR)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGGING_DIR, 'joulia.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB logfiles.
            'backupCount': 10,
        },
    },
    'loggers': {
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propogate': True
        },
        'requests': {
            'level': 'ERROR',
            'handlers': ['console', 'file'],
            'propogate': False
        },
    },
}
