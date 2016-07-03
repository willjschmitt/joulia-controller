'''
Created on Apr 30, 2016

@author: William
'''

brewery_id = 1

host = "//localhost:8888"

datastream_frequency = 1000. #mS

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