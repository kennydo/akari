import logging.config


_logging_config = dict(
    version=1,
    disable_existing_loggers=False,
    formatters={
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
    },
    handlers={
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        }
    },
    loggers={
        '': {
            'handlers': ['console'],
            'level': logging.INFO,
        },
        'influxdb': {
            'level': logging.INFO,
        },
        'phue': {
            'level': logging.INFO,
        },
    },
)
logging.config.dictConfig(_logging_config)
